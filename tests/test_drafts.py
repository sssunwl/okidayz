"""Draft publishing integration checks; all output stays in a temporary directory."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import build


class DraftTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.content = self.root / 'content'
        self.docs = self.root / 'docs'
        self.assets = self.root / 'assets'
        for path in (self.content / 'guide', self.docs, self.assets):
            path.mkdir(parents=True)
        self.patches = patch.multiple(build, ROOT=self.root, CONTENT=self.content,
                                      DOCS=self.docs, ASSETS=self.assets)
        self.patches.start()
        self.addCleanup(self.patches.stop)
        self.addCleanup(build.DRAFTS.clear)
        self.write_post('public', None)
        self.write_post('secret', 'draft')

    def write_post(self, slug, status):
        (self.content / 'guide' / (slug + '.md')).write_text(
            '---\ntitle: Title-' + slug + '\nsummary: Summary-' + slug
            + '\nupdated: 2026-11-27\ntags: [玩]\ncover: sample.jpg\n'
            + (('status: ' + status + '\n') if status is not None else '')
            + 'ig:\n  slides:\n    - Slide\n---\n'
            + 'Hello [guide](../../guide/).\n', encoding='utf-8')

    def run_build(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return build.build_site(events=[], weather=[], updated='2026-11-27 12:00')

    def preview(self):
        token = hashlib.sha256(b'okidayz-draft:guide/secret').hexdigest()[:12]
        return 'preview/' + token + '-secret/'

    def test_visibility_metadata_and_queue(self):
        report = self.run_build()
        public = (self.docs / 'guide/public/index.html').read_text()
        self.assertNotIn('noindex', public)
        preview = (self.docs / self.preview() / 'index.html').read_text()
        self.assertIn('<meta name="robots" content="noindex,nofollow">', preview)
        self.assertIn('<link rel="canonical" href="' + build.SITE_URL + 'guide/secret/">', preview)
        self.assertFalse((self.docs / 'guide/secret').exists())
        for name in ('sitemap.xml', 'guide/index.html', 'index.html', 'ig/index.html', 'guide/public/index.html'):
            self.assertNotIn('secret', (self.docs / name).read_text())
        for reference in ('../../assets/', '../../guide/'):
            self.assertIn(reference, preview)
        # The complete article HTML is identical apart from the robots meta.
        post = build.DRAFTS[0]
        build.build_article(post, build.load_content()['guide'], out_path='expected/secret')
        expected = (self.docs / 'expected/secret/index.html').read_text()
        self.assertEqual(preview.replace('<meta name="robots" content="noindex,nofollow">\n', ''), expected)
        queue = {p['slug']: p for p in json.loads((self.docs / 'ig-queue.json').read_text())}
        self.assertTrue(queue['secret']['draft'])
        self.assertEqual(queue['secret']['preview_url'], build.SITE_URL + self.preview())
        self.assertEqual(queue['secret']['url'], build.SITE_URL + 'guide/secret/')
        self.assertNotIn('draft', queue['public'])
        self.assertNotIn('preview_url', queue['public'])
        self.assertEqual(report['drafts'][0]['preview_url'], build.SITE_URL + self.preview())
        robots = (self.docs / 'robots.txt').read_text()
        self.assertIn('Disallow: /preview/', robots)
        self.assertIn('Allow: /', robots)
        self.assertIn('Sitemap: ' + build.SITE_URL + 'sitemap.xml', robots)

    def test_promotion_removes_preview(self):
        self.run_build()
        self.assertTrue((self.docs / self.preview() / 'index.html').exists())
        self.write_post('secret', 'published')
        report = self.run_build()
        self.assertFalse((self.docs / 'preview').exists())
        self.assertTrue((self.docs / 'guide/secret/index.html').exists())
        self.assertEqual(report['drafts'], [])

    def test_invalid_status_and_invalid_draft_are_skipped(self):
        self.write_post('invalid', 'foo')
        (self.content / 'guide/broken.md').write_text('---\nstatus: draft\n---\nBody')
        self.run_build()
        report = json.loads((self.docs / 'build-report.json').read_text())
        skipped = {p['item']: p['reason'] for p in report['skipped']}
        self.assertIn('status', skipped['content/guide/invalid.md'])
        self.assertIn('缺 title', skipped['content/guide/broken.md'])
        self.assertFalse((self.docs / 'guide/invalid').exists())
        self.assertEqual(len(report['drafts']), 1)


if __name__ == '__main__':
    unittest.main()
