import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from urllib.request import Request

from prepare import (allowed_url, allowed_redirect, collect_evidence, digest, fetch,
                     IntakeRedirectHandler, validate_manifest, validate_source_page,
                     CREATOR_DOWNLOAD, CREATOR_FAQ, CREATOR_IDENTITY,
                     CREATOR_LICENSING, CREATOR_SOURCE, CREATOR_URLS)


class CreatorIntakeTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((Path(__file__).parent / 'ukrainian-shchedryk-20260924.json').read_text())
        self.row = self.manifest['tracks'][0]
        self.source = (f'<div data-src="{CREATOR_DOWNLOAD}"></div>'
                       f'<p>{self.row["licenseURL"]}</p>').encode()
        self.licensing = (f'<a href="{self.row["licenseURL"]}">CC BY 4.0</a>'
                          '<p>My music is in the Smart Content ID database.</p>').encode()

    def test_existing_thirteen_and_ukrainian_manifest_remain_pending(self):
        core = json.loads((Path(__file__).parent / 'core-20260924.json').read_text())
        self.assertEqual(len(validate_manifest(core)['tracks']), 13)
        self.assertIs(validate_manifest(self.manifest), self.manifest)
        self.assertFalse(self.manifest['publicationApproval'])

    def test_creator_urls_are_exact_not_a_host_allowlist(self):
        for url in CREATOR_URLS:
            self.assertTrue(allowed_url(url))
            for changed in (url + '?download=1', url + '#part', url + '/other',
                            url.replace('https://', 'http://'),
                            url.replace('https://', 'https://u:p@'),
                            url.replace('.com/', '.com.evil.test/'),
                            url.replace('.net/', '.net.evil.test/')):
                if changed != url:
                    self.assertFalse(allowed_url(changed), changed)
        for url in ('https://creatorchords.com/music/another-song/',
                    CREATOR_DOWNLOAD.replace('Metal_Version', 'Piano_Version'),
                    CREATOR_DOWNLOAD.replace('cloudfront.net/', 'cloudfront.net:443/'),
                    'https://opengameart.org:bad/path',
                    'https://opengameart.org/line\nbreak'):
            self.assertFalse(allowed_url(url), url)

    def test_recording_identity_and_content_id_cannot_be_changed(self):
        for key in CREATOR_IDENTITY:
            row = copy.deepcopy(self.manifest)
            row['tracks'][0][key] = False if key == 'contentId' else 'changed'
            with self.assertRaises(ValueError, msg=key):
                validate_manifest(row)
        forged = copy.deepcopy(self.manifest)
        forged['tracks'][0]['contentId'] = 1
        with self.assertRaises(ValueError):
            validate_manifest(forged)

    def test_source_and_download_cannot_be_cross_paired(self):
        for key, value in (('source', 'https://opengameart.org/content/song'),
                           ('download', 'https://opengameart.org/sites/default/files/song.mp3'),
                           ('source', CREATOR_FAQ)):
            changed = copy.deepcopy(self.manifest)
            changed['tracks'][0][key] = value
            with self.assertRaises(ValueError):
                validate_manifest(changed)

    def test_exact_data_src_binding_and_oga_relative_encoded_links(self):
        validate_source_page(self.row, self.source)
        oga = {'source': 'https://opengameart.org/content/song',
               'download': 'https://opengameart.org/sites/default/files/my%20song.mp3',
               'licenseURL': 'https://creativecommons.org/publicdomain/zero/1.0/'}
        validate_source_page(oga, b'<a href="/sites/default/files/my%20song.mp3">Song</a>'
                                 b'<a href="http://creativecommons.org/publicdomain/zero/1.0/">CC0</a>')

    def test_source_link_mismatch_and_text_only_url_are_rejected(self):
        for body in (self.source.replace(b'.mp3"', b'.mp3.exe"'),
                     self.source.replace(b'.mp3"', b'.mp3?other=1"'),
                     self.source.replace(b'data-src=', b'data-other='),
                     f'<p>{CREATOR_DOWNLOAD} {self.row["licenseURL"]}</p>'.encode(),
                     self.source.replace(self.row['licenseURL'].encode(), b'no licence')):
            with self.assertRaises(ValueError):
                validate_source_page(self.row, body)

    def test_redirects_rejected_before_requesting_unapproved_destination(self):
        for origin in (CREATOR_SOURCE, CREATOR_DOWNLOAD, 'https://opengameart.org/content/song'):
            handler = IntakeRedirectHandler(origin)
            for target in ('https://evil.test/audio', 'http://opengameart.org/content/song',
                           'https://u:p@opengameart.org/content/song',
                           CREATOR_DOWNLOAD + '?changed=1'):
                with self.assertRaises(ValueError, msg=(origin, target)):
                    handler.redirect_request(Request(origin), None, 302, 'Found', {}, target)
        self.assertFalse(allowed_redirect(CREATOR_SOURCE, CREATOR_DOWNLOAD))
        self.assertFalse(allowed_redirect('https://opengameart.org/content/song', CREATOR_SOURCE))
        self.assertTrue(allowed_redirect('https://opengameart.org/content/song', 'https://opengameart.org/content/canonical-song'))
        request = IntakeRedirectHandler('https://opengameart.org/content/song').redirect_request(
            Request('https://opengameart.org/content/song'), None, 301, 'Moved', {},
            'https://opengameart.org/content/canonical-song')
        self.assertEqual(request.full_url, 'https://opengameart.org/content/canonical-song')

    def test_unapproved_initial_url_never_opens_connection(self):
        with patch('prepare.build_opener') as opener:
            with self.assertRaises(ValueError):
                fetch(CREATOR_DOWNLOAD + '?other', 100)
            opener.assert_not_called()

    def test_creator_snapshots_retain_exact_bytes_hashes_and_content_id_evidence(self):
        bodies = {CREATOR_SOURCE: self.source, CREATOR_LICENSING: self.licensing,
                  CREATOR_FAQ: b'<p>Credit the artist; do not redistribute under your own name.</p>'}
        with TemporaryDirectory() as folder:
            output = Path(folder)
            (output / 'evidence').mkdir()
            with patch('prepare.fetch', side_effect=lambda url, limit: (bodies[url], url)) as mocked:
                partial = {}
                evidence = collect_evidence(self.row, output, {}, partial)
            self.assertEqual(mocked.call_count, 3)
            self.assertEqual(set(evidence), {'sourceSnapshot', 'licensingInfoSnapshot', 'creatorFAQSnapshot'})
            for item in evidence.values():
                raw = (output / item['path']).read_bytes()
                self.assertEqual(raw, bodies[item['url']])
                self.assertEqual(item['sha256'], digest(raw))

    def test_changed_content_id_notice_stops_acquisition_and_retains_snapshots(self):
        with TemporaryDirectory() as folder:
            output = Path(folder)
            (output / 'evidence').mkdir()
            for licensing in (self.licensing.replace(b'Smart Content ID', b'changed notice'),
                              self.licensing.replace(self.row['licenseURL'].encode(), b'changed licence')):
                partial = {}
                bodies = {CREATOR_SOURCE: self.source, CREATOR_LICENSING: licensing,
                          CREATOR_FAQ: b'FAQ'}
                with patch('prepare.fetch', side_effect=lambda url, limit: (bodies[url], url)) as mocked:
                    with self.assertRaises(ValueError):
                        collect_evidence(self.row, output, {}, partial)
                self.assertEqual(mocked.call_count, 3)
                self.assertIn('licensingInfoSnapshot', partial)
                self.assertTrue((output / partial['licensingInfoSnapshot']['path']).is_file())


if __name__ == '__main__':
    unittest.main()
