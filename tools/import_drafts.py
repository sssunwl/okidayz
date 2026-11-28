#!/usr/bin/env python3
"""Import Sona topic drafts. Even --dry-run needs a Supabase read key."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import random
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build
from tools.publish_approved import API


def parse_post(raw, section):
    # Keep the same front matter/body split as load_content().
    if not isinstance(raw, str) or not raw.startswith('---'):
        raise ValueError('缺少 front matter')
    _, _, rest = raw.partition('---')
    front, delimiter, body = rest.partition('\n---')
    if not delimiter:
        raise ValueError('front matter 缺結尾')
    meta = build.parse_front_matter(front)
    meta.update(section=section, body=body.strip())
    return meta


def git(*args, check=True):
    return subprocess.run(['git', *args], cwd=ROOT, check=check,
                          text=True, capture_output=True)


def rebuild():
    subprocess.run([sys.executable, 'build.py'], cwd=ROOT, check=True)


def commit_and_push(slugs, no_push):
    git('add', 'content', 'docs')
    if git('diff', '--cached', '--quiet', check=False).returncode:
        git('commit', '-m', 'drafts: ' + ', '.join(slugs) + ' 自動草稿匯入 [skip ci]')
    if no_push:
        return
    for attempt in range(5):
        if git('push', check=False).returncode == 0:
            return
        result = git('pull', '--rebase', 'origin', 'main', check=False)
        if result.returncode:
            conflicts = git('diff', '--name-only', '--diff-filter=U').stdout.splitlines()
            if not conflicts or any(not p.startswith('docs/') for p in conflicts):
                git('rebase', '--abort', check=False)
                raise RuntimeError('rebase 失敗，含非 docs 衝突')
            for path in conflicts:
                git('restore', '--source=HEAD', '--staged', '--worktree', '--', path)
            rebuild()
            git('add', 'docs')
            git('-c', 'core.editor=true', 'rebase', '--continue')
        if attempt < 4:
            time.sleep(random.randint(5, 14))
    raise RuntimeError('推送重試 5 次仍失敗')


def restore(path, original):
    if original is None:
        path.unlink(missing_ok=True)
    else:
        path.write_bytes(original)


def run(api, dry_run=False, no_push=False):
    summary = {key: [] for key in ('imported', 'revised', 'unchanged', 'blocked', 'errors')}
    ready = []

    def block(row, slug, reason):
        if not dry_run and not api.patch(row, dict(status='blocked', next_action=reason)):
            raise RuntimeError('blocked 更新版本碰撞')
        summary['blocked'].append(dict(slug=slug, reason=reason))

    try:
        brands = api.rows('brands', {'slug': 'eq.okidayz', 'select': 'id'})
        if len(brands) != 1:
            raise ValueError('找不到唯一 okidayz brand')
        rows = api.rows('content_items', {'brand_id': 'eq.' + brands[0]['id'],
                        'metadata->>role': 'eq.topic', 'status': 'eq.producing', 'select': '*'})
        if not rows:
            return summary
        for row in rows:
            slug = row.get('metadata', {}).get('slug')
            try:
                metadata = row.get('metadata') or {}
                section = metadata.get('section')
                if section not in build.SECTIONS or not isinstance(slug, str) or not re.fullmatch(r'[a-z0-9-]+', slug):
                    raise ValueError('section 或 slug 不合法')
                if not row.get('updated_at'):
                    raise ValueError('缺 updated_at')
                raw = metadata.get('draft_md')
                try:
                    meta = parse_post(raw, section)
                    problems = build.validate_post(meta)
                    if meta.get('status') != 'draft':
                        problems.append('status 必須是 draft')
                    if meta.get('slug') != slug:
                        problems.append('slug 與 topic 不符')
                    if problems:
                        raise ValueError('；'.join(problems))
                except (ValueError, TypeError, AttributeError) as exc:
                    block(row, slug, '草稿格式不對:' + str(exc))
                    continue
                path = build.CONTENT / section / (slug + '.md')
                collision = False
                for other_section in build.SECTIONS:
                    for other in (build.CONTENT / other_section).glob('*.md'):
                        other_meta = parse_post(other.read_text(encoding='utf-8'), other_section)
                        other_slug = other_meta.get('slug', other.stem)
                        if other == path:
                            collision |= other_meta.get('status', 'published') != 'draft'
                        elif other.stem == slug or other_slug == slug:
                            collision = True
                if collision:
                    block(row, slug, '網站已有同名正式文章,不覆蓋')
                    continue
                original = path.read_bytes() if path.exists() else None
                content = (raw.rstrip('\r\n') + '\n').encode('utf-8')
                kind = 'imported' if original is None else ('unchanged' if original == content else 'revised')
                if not dry_run and kind != 'unchanged':
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(content)
                ready.append((row, slug, section, path, original, kind))
                summary[kind].append(slug)
            except Exception as exc:
                summary['errors'].append(f'{slug}: {exc}')
        if dry_run or not ready:
            return summary
        changed = [entry for entry in ready if entry[-1] != 'unchanged']
        if changed:
            try:
                rebuild()
                build.load_content()
            except Exception:
                for _, _, _, path, original, kind in changed:
                    restore(path, original)
                raise
            valid = {(p['section'], p['slug']) for p in build.DRAFTS}
            rejected = [entry for entry in ready if (entry[2], entry[1]) not in valid]
            for entry in rejected:
                _, slug, _, path, original, kind = entry
                if kind != 'unchanged':
                    restore(path, original)
                summary[kind].remove(slug)
                summary['errors'].append(f'{slug}: build 後不在 DRAFTS，已還原')
                ready.remove(entry)
            if rejected:
                # Remove any generated preview/queue for files that were restored.
                rebuild()
        if not ready:
            return summary
        commit_and_push([entry[1] for entry in ready], no_push)
        if not no_push:
            for row, slug, section, path, original, kind in ready:
                try:
                    metadata = dict(row['metadata'], imported_at=datetime.now(timezone.utc).isoformat(),
                                    imported_path=f'content/{section}/{slug}.md')
                    if not api.patch(row, dict(status='archived', next_action='已轉成網站草稿', metadata=metadata)):
                        raise RuntimeError('archived 更新版本碰撞')
                except Exception as exc:
                    summary['errors'].append(f'{slug}: {exc}')
    except Exception as exc:
        summary['errors'].append(str(exc))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--no-push', action='store_true')
    args = parser.parse_args()
    key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
    if not key:
        config = Path.home() / '.config/sonasns/supabase.json'
        try:
            if config.exists():
                key = json.loads(config.read_text()).get('service_role_key')
        except (OSError, ValueError):
            print('無法讀取本機 Supabase 設定', file=sys.stderr)
    if key:
        summary = run(API(os.environ.get('SUPABASE_URL', 'https://rtayhbmaqjzygkhurlxq.supabase.co'), key), **vars(args))
    else:
        summary = {k: [] for k in ('imported', 'revised', 'unchanged', 'blocked', 'errors')}
        summary['errors'].append('缺 SUPABASE_SERVICE_ROLE_KEY；dry-run 也需要讀取 Sona')
    print(json.dumps(summary, ensure_ascii=False))
    return bool(summary['errors'])


if __name__ == '__main__':
    sys.exit(main())
