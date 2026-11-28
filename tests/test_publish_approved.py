import io
import json
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from tools import publish_approved as p


class PublishTests(unittest.TestCase):
    def setUp(self):
        self.now = p.parse_time('2026-11-28T11:30:00+09:00')
        self.article = dict(id='a', status='approved', updated_at='2026-11-27T00:00:00Z',
                            scheduled_for=(self.now - timedelta(days=1)).isoformat(),
                            metadata=dict(role='article', article_key='test', site_url='https://example.com/test/'))
        self.ig = dict(id='i', status='approved', updated_at=self.article['updated_at'],
                       scheduled_for=self.article['scheduled_for'], metadata=dict(role='ig', article_key='test'))

    def test_node_hashes(self):
        # Generated with node crypto.createHash('sha256').update(JSON.stringify(obj)).
        self.assertEqual(p.source_hash({'title': 'Title'}),
                         '340e6dcb9dc64b7add51ca927d70693112259a81d3d2c6f8ce2a61c7fb81567c')
        post = dict(title='沖繩😀"\\\t\n', summary='摘要\u2028\u2029', body='正文\x01',
                    ig=dict(cover='封面/', slides=['一', '二'], caption='說明', hashtags=['#沖繩']),
                    sources=['http://excluded/', 'https://example.com/'], ig_at='2026-12-01T12:00:00+09:00')
        self.assertEqual(p.source_hash(post),
                         '0986f3783a874bffa1b532a42c9e10432190a4818a158139c4f07a4b0fc09c57')
        self.assertEqual(p.js_stringify('\ud800'), '"\\ud800"')

    def test_promote_preserves_every_other_byte(self):
        for nl in ('\n', '\r\n'):
            raw = nl.join(['---', '# comment', 'title: "Original"  ', 'status: draft',
                           'updated: 2020-01-01', 'ig:', '  caption: |', '    status: draft',
                           '---', '', 'Body  ', 'status: draft', ''])
            expected = raw.replace('status: draft' + nl + 'updated: 2020-01-01',
                                   'status: published' + nl + 'updated: 2026-11-28')
            expected = expected.replace(nl + '---' + nl, nl + 'published: 2026-11-28' + nl + '---' + nl)
            self.assertEqual(p.promote_text(raw, '2026-11-28'), expected)
        raw = '---\nstatus: draft\ntitle: T\n---\nbody'
        self.assertEqual(p.promote_text(raw, '2026-11-28'),
                         '---\nstatus: published\ntitle: T\nupdated: 2026-11-28\npublished: 2026-11-28\n---\nbody')

    def test_candidates(self):
        self.assertEqual(p.select_candidates([self.article], [self.ig], self.now)[0], [(self.article, self.ig)])
        for changes in ({'status': 'drafting'}, {'scheduled_for': (self.now + timedelta(seconds=1)).isoformat()}):
            self.assertFalse(p.select_candidates([dict(self.article, **changes)], [self.ig], self.now)[0])
        self.assertFalse(p.select_candidates([self.article], [dict(self.ig, status='scheduled')], self.now)[0])
        self.assertFalse(p.select_candidates([self.article], [self.ig, self.ig], self.now)[0])

    def test_changed_patch(self):
        item = dict(self.article, metadata=dict(self.article['metadata'], fact_check={'ok': True}, approval={'by': 'SS'}))
        result = p.changed_patch(item)
        self.assertEqual(result['status'], 'drafting')
        self.assertEqual(result['next_action'], '確認後文章又被改過,待重新查證')
        self.assertEqual(result['metadata']['fact_check_prev'], {'ok': True})
        self.assertNotIn('fact_check', result['metadata'])
        self.assertNotIn('approval', result['metadata'])
        self.assertIn('approval', item['metadata'])

    def test_finalization(self):
        a, ig = p.final_patches(self.article, self.ig, self.now, True)
        self.assertEqual(a, dict(status='published', published_at=self.now.isoformat(),
                                published_url=self.article['metadata']['site_url'], next_action='網站已上線'))
        self.assertEqual(ig['status'], 'scheduled')
        self.assertEqual(ig['scheduled_for'], '2026-11-29T12:00:00+09:00')
        self.assertIn('原時間已過', ig['next_action'])
        for hour, expected in ((10, '2026-11-28T12:00:00+09:00'), (11, '2026-11-28T12:00:00+09:00'), (12, '2026-11-29T12:00:00+09:00')):
            now = self.now.replace(hour=hour, minute=0)
            self.assertEqual(p.final_patches(self.article, self.ig, now, True)[1]['scheduled_for'], expected)
        future = dict(self.ig, scheduled_for=(self.now + timedelta(minutes=30)).isoformat())
        self.assertNotIn('scheduled_for', p.final_patches(self.article, future, self.now, True)[1])

    def test_wait_non_200_and_no_patches(self):
        ticks = [0]
        class Response(io.BytesIO):
            status = 404
        def sleep(seconds):
            ticks[0] += seconds
        live = p.wait_live('https://example.com/', opener=lambda *a, **kw: Response(),
                           clock=lambda: ticks[0], sleep=sleep, timeout=60)
        self.assertFalse(live)
        self.assertEqual(ticks[0], 60)
        self.assertEqual(p.final_patches(self.article, self.ig, self.now, live), [])

    def test_fake_http_cas(self):
        requests = []
        def opener(req, **kwargs):
            requests.append(req)
            return io.BytesIO(b'[]')
        api = p.API('https://example.com', 'fake', opener)
        self.assertFalse(api.patch(self.article, {'status': 'published'}))
        self.assertIn('updated_at=eq.', requests[0].full_url)
        self.assertEqual(requests[0].method, 'PATCH')
        self.assertEqual(json.loads(requests[0].data), {'status': 'published'})

    def test_dry_run_without_key(self):
        with patch.dict(p.os.environ, {}, clear=True), patch.object(p.Path, 'exists', return_value=False), patch.object(p.sys, 'argv', ['publish_approved.py', '--dry-run']), patch('sys.stdout', new_callable=io.StringIO) as output:
            self.assertTrue(p.main())
        summary = json.loads(output.getvalue())
        self.assertIn('dry-run', summary['errors'][0])

    def test_no_candidates_does_not_build_or_git(self):
        class FakeAPI:
            def rows(self, table, params):
                return [{'id': 'brand'}] if table == 'brands' else []
        with patch.object(p.build, 'build_site', side_effect=AssertionError('build')), patch.object(p, 'git', side_effect=AssertionError('git')):
            summary = p.run(FakeAPI())
        self.assertFalse(summary['errors'])


if __name__ == '__main__':
    unittest.main()
