#!/usr/bin/env python3
"""Poll approved OkiDayz articles; dry-run never writes, builds or runs git."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build

JST = timezone(timedelta(hours=9))


def parse_time(value):
    result = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('時間缺時區')
    return result


def js_stringify(value):
    """JSON.stringify-compatible strings, including well-formed lone surrogates."""
    result = json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    return ''.join('\\u%04x' % ord(c) if 0xd800 <= ord(c) <= 0xdfff else c for c in result)


def source_hash(post):
    ig = post.get('ig') or {}
    obj = dict(title=post['title'], summary=post.get('summary') or '',
               body=post.get('body') or '', cover=ig.get('cover') or post['title'],
               slides=ig.get('slides') or [], caption=ig.get('caption') or '',
               hashtags=ig.get('hashtags') or [],
               sources=[str(s) for s in (post.get('sources') or []) if str(s).startswith('https://')],
               ig_at=str(post.get('ig_at') or ''))
    return hashlib.sha256(js_stringify(obj).encode('utf-8')).hexdigest()


def promote_text(raw, today):
    lines = raw.splitlines(keepends=True)
    if not lines or lines[0].strip() != '---':
        raise ValueError('缺 front matter')
    end = next(i for i in range(1, len(lines)) if lines[i].strip() == '---')
    newline = '\r\n' if lines[0].endswith('\r\n') else '\n'
    found = set()
    for i in range(1, end):
        match = re.match(r'^(status|updated|published):(.*?)(\r?\n)?$', lines[i])
        if not match:
            continue
        key = match[1]
        if key in found:
            raise ValueError('重複 front matter 欄位: ' + key)
        found.add(key)
        lines[i] = f'{key}: {"published" if key == "status" else today}{match[3] or ""}'
    if 'status' not in found:
        raise ValueError('缺 status')
    lines[end:end] = [f'{key}: {today}{newline}' for key in ('updated', 'published') if key not in found]
    return ''.join(lines)


def select_candidates(articles, ig_items, now):
    pairs, skipped = [], []
    for article in articles:
        if article['status'] != 'approved':
            continue
        if not article.get('scheduled_for') or parse_time(article['scheduled_for']) > now:
            continue
        key = article.get('metadata', {}).get('article_key')
        matches = [ig for ig in ig_items if key and ig.get('metadata', {}).get('article_key') == key]
        if len(matches) != 1 or matches[0]['status'] != 'approved':
            skipped.append(key or article['id'])
        else:
            pairs.append((article, matches[0]))
    return pairs, skipped


def changed_patch(item):
    metadata = dict(item.get('metadata') or {})
    if 'fact_check' in metadata:
        metadata['fact_check_prev'] = metadata.pop('fact_check')
    metadata.pop('approval', None)
    return dict(status='drafting', next_action='確認後文章又被改過,待重新查證', metadata=metadata)


def final_patches(article, ig, now, live):
    if not live:
        return []
    ig_patch = dict(status='scheduled', next_action='已批准,等發佈')
    if not ig.get('scheduled_for') or parse_time(ig['scheduled_for']) < now + timedelta(minutes=30):
        noon = now.astimezone(JST).replace(hour=12, minute=0, second=0, microsecond=0)
        while noon < now + timedelta(hours=1):
            noon += timedelta(days=1)
        ig_patch.update(scheduled_for=noon.isoformat(), next_action=f'已批准,等發佈；原時間已過,改到 {noon.isoformat()}')
    return [dict(status='published', published_at=now.isoformat(),
                 published_url=article['metadata']['site_url'], next_action='網站已上線'), ig_patch]


class API:
    def __init__(self, url, key, opener=urlopen):
        self.url, self.key, self.opener = url.rstrip('/'), key, opener

    def request(self, table, params, payload=None):
        headers = {'apikey': self.key, 'Authorization': 'Bearer ' + self.key,
                   'Content-Type': 'application/json', 'Prefer': 'return=representation'}
        req = Request(self.url + '/rest/v1/' + table + '?' + urlencode(params), headers=headers,
                      data=None if payload is None else json.dumps(payload, ensure_ascii=False).encode(),
                      method='GET' if payload is None else 'PATCH')
        with self.opener(req, timeout=30) as response:
            return json.load(response)

    def rows(self, table, params):
        result, offset = [], 0
        while True:
            page = self.request(table, dict(params, order='id.asc', limit=500, offset=offset))
            result.extend(page)
            if len(page) < 500:
                return result
            offset += len(page)

    def patch(self, item, payload):
        if not item.get('updated_at'):
            raise ValueError('缺 updated_at: ' + item['id'])
        rows = self.request('content_items', {'id': 'eq.' + item['id'],
                            'updated_at': 'eq.' + item['updated_at'], 'status': 'eq.' + item['status']}, payload)
        if not rows:
            print('版本碰撞，下次再處理: ' + item['id'])
            return False
        return True


def wait_live(url, opener=urlopen, sleep=time.sleep, clock=time.monotonic, timeout=600):
    if urlsplit(url).scheme not in ('http', 'https'):
        raise ValueError('不允許的網站 URL')
    deadline = clock() + timeout
    while True:
        try:
            with opener(Request(url, headers={'User-Agent': 'OkiDayz-publish/1.0'}),
                        timeout=max(1, min(20, deadline - clock()))) as response:
                if response.status == 200:
                    return True
        except (HTTPError, URLError, TimeoutError):
            pass
        remaining = deadline - clock()
        if remaining <= 0:
            return False
        sleep(min(30, remaining))


def git(*args, check=True):
    return subprocess.run(['git', *args], cwd=ROOT, check=check, text=True, capture_output=True)


def commit_and_push(slugs, no_push):
    build.build_site()
    git('add', 'content', 'docs')
    git('commit', '-m', 'publish: ' + ', '.join(slugs) + ' 文章上線 [skip ci]')
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
            # During rebase ours is the remote base, theirs is our replayed commit.
            for path in conflicts:
                git('restore', '--source=HEAD', '--staged', '--worktree', '--', path)
            build.build_site()
            git('add', 'docs')
            git('-c', 'core.editor=true', 'rebase', '--continue')
        time.sleep(random.randint(5, 14))
    raise RuntimeError('推送重試 5 次仍失敗')


def run(api, dry_run=False, no_push=False):
    summary = {key: [] for key in ('published', 'live', 'waiting', 'changed', 'skipped', 'errors')}
    try:
        brands = api.rows('brands', {'slug': 'eq.okidayz', 'select': 'id'})
        if len(brands) != 1:
            raise ValueError('找不到唯一 okidayz brand')
        base = {'brand_id': 'eq.' + brands[0]['id'], 'select': '*'}
        articles = api.rows('content_items', dict(base, **{'metadata->>role': 'eq.article'}))
        relevant = [a for a in articles if a['status'] in ('approved', 'published')]
        if not relevant:
            return summary
        ig_items = api.rows('content_items', dict(base, **{'metadata->>role': 'eq.ig'}))
        now = datetime.now(timezone.utc)
        pairs, summary['skipped'] = select_candidates(articles, ig_items, now)
        # Recover a partial finalization: article PATCH succeeded, IG PATCH collided.
        for a in relevant:
            if a['status'] == 'published':
                matches = [i for i in ig_items if i.get('metadata', {}).get('article_key') == a.get('metadata', {}).get('article_key') and i['status'] == 'approved']
                if len(matches) == 1:
                    pairs.append((a, matches[0]))
        if not pairs:
            return summary
        posts = build.load_content()
        drafts = {p['slug']: p for p in build.DRAFTS}
        public = {p['slug']: p for group in posts.values() for p in group}
        ready = []
        for article, ig in pairs:
            slug = article['metadata']['article_key']
            try:
                post = drafts.get(slug)
                if post:
                    if source_hash(post) != article['metadata'].get('source_hash'):
                        if not dry_run:
                            for item in (article, ig):
                                api.patch(item, changed_patch(item))
                        summary['changed'].append(slug)
                        continue
                    paths = [p for p in (build.CONTENT / post['section']).glob('*.md')
                             if build.parse_front_matter(p.read_text(encoding='utf-8').split('---', 2)[1]).get('slug', p.stem) == slug]
                    if len(paths) != 1:
                        raise ValueError('無法唯一定位文章檔案')
                    path = paths[0]
                    raw = path.read_bytes().decode('utf-8')
                    promoted = promote_text(raw, now.astimezone(JST).date().isoformat())
                    if not dry_run:
                        path.write_bytes(promoted.encode('utf-8'))
                    summary['published'].append(slug)
                elif slug not in public:
                    print('警告：找不到文章 ' + slug)
                    summary['skipped'].append(slug)
                    continue
                ready.append((article, ig))
            except Exception as exc:
                summary['errors'].append(f'{slug}: {exc}')
        if summary['published'] and not dry_run:
            commit_and_push(summary['published'], no_push)
        for article, ig in ready:
            slug = article['metadata']['article_key']
            if dry_run or no_push:
                print(f'{slug}: 待部署後驗證網址與收尾' if no_push else f'{slug}: 計畫驗證網址、文章 published、IG scheduled')
                summary['waiting'].append(slug)
                continue
            try:
                if not wait_live(article['metadata']['site_url']):
                    print(f'{slug}: 網站還沒上線,下次再確認')
                    summary['waiting'].append(slug)
                    continue
                a_patch, i_patch = final_patches(article, ig, datetime.now(timezone.utc), True)
                if article['status'] != 'published' and not api.patch(article, a_patch):
                    summary['waiting'].append(slug)
                    continue
                if api.patch(ig, i_patch):
                    summary['live'].append(slug)
                else:
                    summary['waiting'].append(slug)
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
    if not key:
        summary = {k: [] for k in ('published', 'live', 'waiting', 'changed', 'skipped', 'errors')}
        summary['errors'].append('缺 SUPABASE_SERVICE_ROLE_KEY；dry-run 也需要讀取 Sona')
    else:
        summary = run(API(os.environ.get('SUPABASE_URL', 'https://rtayhbmaqjzygkhurlxq.supabase.co'), key), **vars(args))
    print(json.dumps(summary, ensure_ascii=False))
    return bool(summary['errors'])


if __name__ == '__main__':
    sys.exit(main())
