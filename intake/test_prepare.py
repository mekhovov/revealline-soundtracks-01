import copy
import hashlib
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
from prepare import (allowed_redirect, allowed_url, candidate_duration_bounds,
                     commons_api_url, commons_metadata, validate_commons_original, validate_manifest,
                     reserve, reserve_row, verify_inspector, COMMONS_CHANGE_NOTICE,
                     RESERVE, SOURCE_LIMIT, TOTAL_LIMIT)


class IntakeTests(unittest.TestCase):
    def setUp(self):
        self.value = {'format': 'revealline-core-intake.v1', 'tracks': [{
            'id': 'artist.song', 'source': 'https://opengameart.org/content/song',
            'download': 'https://opengameart.org/sites/default/files/song.mp3',
            'license': 'CC0 1.0 Universal', 'licenseURL': 'https://creativecommons.org/publicdomain/zero/1.0/',
            'status': 'rights-reviewed-listening-pending'}]}

    def test_valid_pending_intake(self):
        self.assertIs(validate_manifest(self.value), self.value)

    def test_unknown_hosts_and_credentials(self):
        for url in ('http://opengameart.org/a', 'https://evil.test/a', 'https://u:p@opengameart.org/a', 'https://opengameart.org:444/a'):
            self.assertFalse(allowed_url(url))

    def test_duplicate_and_traversal_ids(self):
        for identifier in ('../song', '/song', 'a/b'):
            item = copy.deepcopy(self.value)
            item['tracks'][0]['id'] = identifier
            with self.assertRaises(ValueError): validate_manifest(item)
        self.value['tracks'] *= 2
        with self.assertRaises(ValueError): validate_manifest(self.value)

    def test_short_candidate_envelope_is_limited_to_explicit_boss_cues(self):
        self.assertEqual(candidate_duration_bounds({}), (60, 720))
        self.assertEqual(candidate_duration_bounds({'role': 'gameplay'}), (60, 720))
        self.assertEqual(candidate_duration_bounds({'role': 'menu'}), (60, 720))
        self.assertEqual(candidate_duration_bounds({'role': 'boss-cue'}), (30, 720))
        self.assertEqual(candidate_duration_bounds({'role': 'Boss-Cue'}), (60, 720))

    def test_no_licence_or_listening_escalation(self):
        for key, value in (('licenseURL', 'https://example.com/free'), ('status', 'approved'), ('download', 'https://opengameart.org/preview')):
            item = copy.deepcopy(self.value)
            item['tracks'][0][key] = value
            with self.assertRaises(ValueError): validate_manifest(item)

    def test_reserve_accounts_for_derivative_and_evidence(self):
        with patch('prepare.shutil.disk_usage', return_value=SimpleNamespace(free=RESERVE + 64 * 1024 ** 2)):
            with self.assertRaises(ValueError): reserve(Path('.'))

    def test_retained_budget_refuses_before_next_row(self):
        with TemporaryDirectory() as folder:
            file = Path(folder) / 'retained'
            with file.open('wb') as handle: handle.truncate(TOTAL_LIMIT - 90 * 1024 ** 2)
            with self.assertRaises(ValueError): reserve_row(Path(folder))

    def test_inspector_revision_is_verified_before_acquisition(self):
        with patch('prepare.command', return_value=SimpleNamespace(stdout='wrong-revision\n')):
            with self.assertRaises(ValueError): verify_inspector(Path('.'))


class CommonsIntakeTests(unittest.TestCase):
    def setUp(self):
        self.title = 'File:Example Ukrainian recording.webm'
        self.source = 'https://commons.wikimedia.org/wiki/File:Example_Ukrainian_recording.webm'
        self.row = {
            'id': 'artist.example', 'title': 'Example', 'artist': 'Artist',
            'source': self.source, 'acquisition': 'wikimedia-commons-original',
            'commonsTitle': self.title, 'license': 'CC BY 3.0 Unported',
            'commonsBytes': 9_588_148, 'commonsSha1': 'a' * 40,
            'licenseURL': 'https://creativecommons.org/licenses/by/3.0/',
            'credit': 'Example by Artist. CC BY 3.0: https://creativecommons.org/licenses/by/3.0/.',
            'changes': COMMONS_CHANGE_NOTICE, 'contentId': None,
            'recordingModeEligible': False, 'culturalReview': 'pending',
            'instrumentalReview': 'pending', 'fullTrackListening': False,
            'gameplayReview': 'pending', 'status': 'rights-reviewed-listening-pending',
        }
        self.manifest = {
            'format': 'revealline-core-intake.v1', 'batch': 'commons-test',
            'publicationApproval': False, 'gameCatalogueAdmission': False,
            'listeningApproval': False, 'tracks': [self.row],
        }
        self.info = {
            'url': ('https://upload.wikimedia.org/wikipedia/commons/a/ab/Example_Ukrainian_recording.webm'
                    '?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original'),
            'descriptionurl': self.source, 'size': 9_588_148,
            'mime': 'video/webm', 'mediatype': 'VIDEO', 'sha1': 'a' * 40,
            'extmetadata': {
                'LicenseUrl': {'value': 'https://creativecommons.org/licenses/by/3.0'},
                'LicenseShortName': {'value': 'CC BY 3.0'},
            },
        }

    def api_body(self, info=None, pages=None):
        value = {'query': {'pages': pages if pages is not None else [{
            'pageid': 1, 'ns': 6, 'title': self.title,
            'imageinfo': [self.info if info is None else info],
        }]}}
        return json.dumps(value).encode()

    def test_exact_pending_commons_manifest_and_urls(self):
        self.assertIs(validate_manifest(self.manifest), self.manifest)
        api = commons_api_url(self.title)
        self.assertTrue(allowed_url(api))
        self.assertTrue(allowed_url(self.source))
        self.assertTrue(allowed_url(self.info['url']))
        self.assertFalse(allowed_url('https://commons.wikimedia.org/wiki/Main_Page'))
        self.assertFalse(allowed_url('https://upload.wikimedia.org/wikipedia/commons/a/ab/file.webm?x=1'))
        self.assertFalse(allowed_url(commons_api_url('File:one.webm|File:two.webm')))

    def test_checked_in_ukrainian_commons_manifest_validates(self):
        path = Path(__file__).with_name('ukrainian-commons-audition-20260925.json')
        value = json.loads(path.read_text())
        self.assertIs(validate_manifest(value), value)

    def test_commons_manifest_fails_closed(self):
        mutations = (
            ('commonsTitle', 'File:Other.webm'),
            ('download', self.info['url']),
            ('commonsBytes', 0),
            ('commonsSha1', 'short'),
            ('contentId', False),
            ('recordingModeEligible', True),
            ('culturalReview', 'approved'),
            ('fullTrackListening', True),
            ('changes', 'Converted.'),
            ('licenseURL', 'https://creativecommons.org/licenses/by/4.0/'),
        )
        for key, value in mutations:
            with self.subTest(key=key):
                manifest = copy.deepcopy(self.manifest)
                manifest['tracks'][0][key] = value
                with self.assertRaises(ValueError):
                    validate_manifest(manifest)
        manifest = copy.deepcopy(self.manifest)
        manifest['publicationApproval'] = True
        with self.assertRaises(ValueError):
            validate_manifest(manifest)

    def test_commons_api_binds_one_bounded_licensed_original(self):
        metadata = commons_metadata(self.row, self.api_body())
        self.assertEqual(metadata['url'], self.info['url'])
        self.assertEqual(metadata['bytes'], self.info['size'])
        self.assertEqual(metadata['sha1'], self.info['sha1'])

    def test_commons_downloaded_bytes_match_the_api_revision(self):
        body = b'exact reviewed Commons original'
        metadata = {
            'url': self.info['url'],
            'bytes': len(body),
            'sha1': hashlib.sha1(body, usedforsecurity=False).hexdigest(),
        }
        self.assertIsNone(validate_commons_original(metadata, body, self.info['url']))

        substituted = b'same length substituted payload'
        self.assertEqual(len(substituted), len(body))
        with self.assertRaisesRegex(ValueError, 'SHA-1'):
            validate_commons_original(metadata, substituted, self.info['url'])

    def test_commons_api_rejects_ambiguous_or_changed_metadata(self):
        cases = []
        cases.append(self.api_body(pages=[]))
        cases.append(self.api_body(pages=[
            {'title': self.title, 'imageinfo': [self.info]},
            {'title': 'File:Other.webm', 'imageinfo': [self.info]},
        ]))
        for key, value in (
            ('descriptionurl', 'https://commons.wikimedia.org/wiki/File:Other.webm'),
            ('url', 'https://evil.example/file.webm'),
            ('size', SOURCE_LIMIT + 1),
            ('mime', 'audio/ogg'),
            ('mediatype', 'AUDIO'),
            ('sha1', ''),
        ):
            info = copy.deepcopy(self.info)
            info[key] = value
            cases.append(self.api_body(info=info))
        info = copy.deepcopy(self.info)
        info['sha1'] = 'b' * 40
        cases.append(self.api_body(info=info))
        info = copy.deepcopy(self.info)
        info['extmetadata']['LicenseUrl']['value'] = 'https://creativecommons.org/licenses/by/4.0/'
        cases.append(self.api_body(info=info))
        for body in cases:
            with self.subTest(body=body[:100]):
                with self.assertRaises(ValueError):
                    commons_metadata(self.row, body)

    def test_commons_redirects_never_cross_hosts(self):
        api = commons_api_url(self.title)
        self.assertFalse(allowed_redirect(api, self.info['url']))
        self.assertFalse(allowed_redirect(self.info['url'], 'https://evil.example/file.webm'))
        self.assertTrue(allowed_redirect(self.info['url'], self.info['url']))


if __name__ == '__main__':
    unittest.main()
