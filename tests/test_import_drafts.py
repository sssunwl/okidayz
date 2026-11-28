import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from tools import import_drafts as p


class ImportTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.content = self.root / 'content'
        self.content.mkdir()
        patches = patch.multiple(p.build, ROOT=self.root, CONTENT=self.content)
        patches.start()
        self.addCleanup(patches.stop)
        root_patch = patch.object(p, 'ROOT', self.root)
        root_patch.start()
        self.addCleanup(root_patch.stop)
        self.addCleanup(p.build.DRAFTS.clear)
        self.raw = '---\ntitle: 沖繩\nsummary: 摘要\nslug: test\nstatus: draft\n---\n正文\n'
        self.row = dict(id='topic', status='producing', updated_at='2026-11-28T00:00:00Z',
                        metadata=dict(role='topic', slug='test', section='guide', draft_md=self.raw))
        self.requests = []
        self.rows = [self.row]
        self.api = p.API('https://example.com', 'fake', self.opener)
        self.rebuild = patch.object(p, 'rebuild').start()
        self.addCleanup(patch.stopall)
        self.real_ship = p.commit_and_push
        self.ship = patch.object(p, 'commit_and_push').start()
        self.path = self.content / 'guide/test.md'

    def opener(self, req, **kwargs):
        self.requests.append(req)
        query = parse_qs(urlsplit(req.full_url).query)
        if req.method == 'PATCH':
            self.assertEqual(query['updated_at'], ['eq.' + self.row['updated_at']])
            self.assertEqual(query['status'], ['eq.producing'])
            return io.BytesIO(b'[{"id":"topic"}]')
        if '/brands?' in req.full_url:
            result = [{'id': 'brand'}]
        else:
            self.assertEqual(query['status'], ['eq.producing'])
            self.assertEqual(query['metadata->>role'], ['eq.topic'])
            result = self.rows
        return io.BytesIO(json.dumps(result).encode())

    def payloads(self):
        return [json.loads(r.data) for r in self.requests if r.method == 'PATCH']

    def write(self, raw, section='guide', filename='test'):
        path = self.content / section / (filename + '.md')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(raw, encoding='utf-8')
        return path

    def test_new_archived_after_push(self):
        self.ship.side_effect = lambda *a: self.assertEqual(self.payloads(), [])
        result = p.run(self.api)
        self.assertFalse(result['errors'])
        self.assertEqual(result['imported'], ['test'])
        self.assertEqual(self.path.read_bytes(), self.raw.encode())
        payload = self.payloads()[0]
        self.assertEqual(payload['status'], 'archived')
        self.assertEqual(payload['next_action'], '已轉成網站草稿')
        self.assertEqual(payload['metadata']['imported_path'], 'content/guide/test.md')
        self.assertEqual(payload['metadata']['draft_md'], self.raw)
        p.datetime.fromisoformat(payload['metadata']['imported_at'])

    def test_revised_then_unchanged_still_archived(self):
        self.write(self.raw.replace('正文', '舊文'))
        self.assertEqual(p.run(self.api)['revised'], ['test'])
        self.requests.clear()
        self.rebuild.reset_mock()
        result = p.run(self.api)
        self.assertEqual(result['unchanged'], ['test'])
        self.assertEqual(self.payloads()[0]['status'], 'archived')
        self.rebuild.assert_not_called()
        self.ship.assert_called()

    def test_published_and_other_section(self):
        for section, raw in [('guide', self.raw.replace('status: draft', 'status: published')),
                             ('ocean', self.raw)]:
            with self.subTest(section=section):
                path = self.write(raw, section)
                self.requests.clear()
                result = p.run(self.api)
                self.assertEqual(result['blocked'][0]['slug'], 'test')
                self.assertEqual(self.payloads()[0]['next_action'], '網站已有同名正式文章,不覆蓋')
                self.assertEqual(path.read_text(), raw)
                path.unlink()
        self.rebuild.assert_not_called()
        self.ship.assert_not_called()

    def test_invalid_drafts(self):
        for raw, reason in [(self.raw.replace('summary: 摘要\n', ''), '缺 summary'),
                            (self.raw.replace('status: draft', 'status: published'), 'status 必須'),
                            (self.raw.replace('slug: test', 'slug: wrong'), 'slug 與 topic'),
                            ('---\nstatus: draft', '缺結尾')]:
            with self.subTest(reason=reason):
                self.row['metadata']['draft_md'] = raw
                self.requests.clear()
                result = p.run(self.api)
                self.assertFalse(result['errors'])
                self.assertEqual(self.payloads()[0]['status'], 'blocked')
                self.assertIn(reason, self.payloads()[0]['next_action'])
                self.assertFalse(self.path.exists())

    def test_build_rejection_restores_new_and_existing(self):
        for existing in (False, True):
            with self.subTest(existing=existing):
                original = self.raw.replace('正文', '舊文')
                if existing:
                    self.write(original)
                with patch.object(p.build, 'load_content', side_effect=p.build.DRAFTS.clear):
                    result = p.run(self.api)
                self.assertTrue(result['errors'])
                self.assertEqual(result['imported'], [])
                self.assertEqual(result['revised'], [])
                if existing:
                    self.assertEqual(self.path.read_text(), original)
                else:
                    self.assertFalse(self.path.exists())
        self.ship.assert_not_called()
        self.assertEqual(self.payloads(), [])

    def test_build_failure_restores(self):
        self.rebuild.side_effect = RuntimeError('build failed')
        self.assertTrue(p.run(self.api)['errors'])
        self.assertFalse(self.path.exists())
        self.ship.assert_not_called()

    def test_no_rows(self):
        self.rows = []
        self.assertFalse(p.run(self.api)['errors'])
        self.rebuild.assert_not_called()
        self.ship.assert_not_called()

    def test_push_failure_and_no_push_do_not_archive(self):
        self.ship.side_effect = RuntimeError('push failed')
        self.assertTrue(p.run(self.api)['errors'])
        self.assertEqual(self.payloads(), [])
        self.ship.side_effect = None
        self.assertFalse(p.run(self.api, no_push=True)['errors'])
        self.assertEqual(self.payloads(), [])
        self.ship.assert_called_with(['test'], True)

    def test_dry_run_and_bad_location(self):
        self.assertEqual(p.run(self.api, dry_run=True)['imported'], ['test'])
        self.assertFalse(self.path.exists())
        self.assertEqual(self.payloads(), [])
        self.row['metadata']['slug'] = '../bad'
        self.assertTrue(p.run(self.api)['errors'])
        self.rebuild.assert_not_called()
        self.ship.assert_not_called()

    def test_dry_run_without_key(self):
        with patch.dict(p.os.environ, {}, clear=True), patch.object(p.Path, 'exists', return_value=False), patch.object(p.sys, 'argv', ['import_drafts.py', '--dry-run']), patch('sys.stdout', new_callable=io.StringIO) as output:
            self.assertTrue(p.main())
        self.assertIn('dry-run', json.loads(output.getvalue())['errors'][0])

    def test_git_commit_and_no_push(self):
        from types import SimpleNamespace
        def fake_git(*args, **kwargs):
            code = 1 if args[:3] == ('diff', '--cached', '--quiet') else 0
            return SimpleNamespace(returncode=code, stdout='')
        with patch.object(p, 'git', side_effect=fake_git) as git:
            self.real_ship(['test'], False)
        self.assertIn(('add', 'content', 'docs'), [c.args for c in git.call_args_list])
        self.assertIn(('commit', '-m', 'drafts: test 自動草稿匯入 [skip ci]'), [c.args for c in git.call_args_list])
        with patch.object(p, 'git', side_effect=fake_git) as git:
            self.real_ship(['test'], True)
        self.assertNotIn(('push',), [c.args for c in git.call_args_list])

    def test_git_retry_docs_conflict(self):
        from types import SimpleNamespace
        pushes = []
        def fake_git(*args, **kwargs):
            code, stdout = 0, ''
            if args == ('push',):
                pushes.append(1)
                code = int(len(pushes) == 1)
            elif args[:2] == ('pull', '--rebase'):
                code = 1
            elif args == ('diff', '--name-only', '--diff-filter=U'):
                stdout = 'docs/index.html\n'
            return SimpleNamespace(returncode=code, stdout=stdout)
        with patch.object(p, 'git', side_effect=fake_git) as git, patch.object(p.time, 'sleep'):
            self.real_ship(['test'], False)
        self.assertEqual(len(pushes), 2)
        self.rebuild.assert_called_once()
        self.assertIn(('restore', '--source=HEAD', '--staged', '--worktree', '--', 'docs/index.html'),
                      [c.args for c in git.call_args_list])


if __name__ == '__main__':
    unittest.main()
