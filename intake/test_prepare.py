import copy
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
from prepare import (allowed_url, candidate_duration_bounds, validate_manifest,
                     reserve, reserve_row, verify_inspector, RESERVE, TOTAL_LIMIT)


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


if __name__ == '__main__':
    unittest.main()
