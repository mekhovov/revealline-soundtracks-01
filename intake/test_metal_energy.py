import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import prepare_metal_energy as entry


class MetalEnergyTests(unittest.TestCase):
    def setUp(self):
        self.raw = entry.MANIFEST.read_bytes()
        self.manifest = entry.checked_manifest(self.raw)
        self.rows = self.manifest['tracks']

    def test_exact_pending_slate_and_style_split(self):
        self.assertEqual(len(self.rows), 8)
        self.assertEqual([row['family'] for row in self.rows], ['metal'] * 5 + ['synth90s'] * 3)
        for flag in ('publicationApproval', 'gameCatalogueAdmission',
                     'defaultPlaylistAdmission', 'recordingModeAdmission',
                     'listeningApproval'):
            self.assertIs(self.manifest[flag], False)
        for row in self.rows:
            self.assertEqual(row['status'], 'rights-reviewed-listening-pending')
            self.assertIs(row['auditionOnly'], True)
            self.assertIs(row['defaultPlaylistEligible'], False)
            self.assertIs(row['recordingModeEligible'], False)
            self.assertIs(row['fullTrackListening'], False)
            self.assertEqual(row['instrumentalReview'], 'pending')
            self.assertEqual(row['gameplayReview'], 'pending')

    def test_exact_rights_and_creator_download_hosts(self):
        expected = {
            'CC0 1.0 Universal': 'https://creativecommons.org/publicdomain/zero/1.0/',
            'CC BY 3.0 Unported': 'https://creativecommons.org/licenses/by/3.0/',
            'CC BY 4.0 International': 'https://creativecommons.org/licenses/by/4.0/',
        }
        self.assertEqual({row['license'] for row in self.rows}, set(expected))
        for row in self.rows:
            self.assertEqual(row['licenseURL'], expected[row['license']])
            self.assertTrue(row['source'].startswith('https://opengameart.org/content/'))
            self.assertTrue(row['download'].startswith('https://opengameart.org/sites/default/files/'))
            self.assertTrue(row['credit'].strip())
            self.assertTrue(row['changes'].strip())

    def test_content_id_and_high_energy_metadata_fail_closed(self):
        beetlemuse = {row['id']: row for row in self.rows if row['artist'] == 'Beetlemuse'}
        self.assertEqual(set(beetlemuse), {'beetlemuse.nox-venator', 'beetlemuse.rabidus'})
        self.assertTrue(all(row['contentId'] is True for row in beetlemuse.values()))
        for row in self.rows:
            self.assertIn(row['energy'], ('medium-high', 'high'))
            self.assertIn(row['role'], ('gameplay', 'boss-cue'))
            self.assertGreaterEqual(len(row['substyles']), 2)
            if row['artist'] != 'Beetlemuse':
                self.assertEqual(row['contentId'], 'unknown')

    def test_manifest_hash_and_bound_source_files_are_exact(self):
        self.assertEqual(hashlib.sha256(self.raw).hexdigest(), entry.MANIFEST_SHA256)
        self.assertEqual(len(entry.SOURCE_FILES), len(set(entry.SOURCE_FILES)))
        self.assertTrue(all(Path(name).is_file() for name in entry.SOURCE_FILES))
        changed = copy.deepcopy(self.manifest)
        changed['tracks'][0]['listeningApproval'] = True
        with self.assertRaisesRegex(ValueError, 'Immutable'):
            entry.checked_manifest(json.dumps(changed).encode())

    @staticmethod
    def hosted_env():
        return {
            'GITHUB_ACTIONS': 'true',
            'GITHUB_REPOSITORY': 'mekhovov/revealline-soundtracks-01',
            'GITHUB_SHA': 'a' * 40,
            'EVENT_HEAD_SHA': 'b' * 40,
            'GITHUB_WORKFLOW_REF': (
                'mekhovov/revealline-soundtracks-01/'
                + entry.WORKFLOW
                + '@refs/pull/28/merge'
            ),
            'GITHUB_RUN_ID': '123',
        }

    def test_local_acquisition_is_refused(self):
        with patch.dict('os.environ', {}, clear=True), patch.object(entry, 'prepare') as acquire:
            with self.assertRaisesRegex(ValueError, 'distinct hosted'):
                entry.run(Path('unused-output'), Path('unused-runtime'))
            acquire.assert_not_called()

    def test_partial_failure_preserves_exact_binding_without_approval(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'evidence'

            def partial(manifest, destination, runtime):
                destination.mkdir()
                (destination / 'receipt.json').write_text('{"failures":[{"error":"fixture"}]}')
                raise ValueError('fixture failure')

            with patch.dict('os.environ', self.hosted_env(), clear=True), patch.object(
                entry, 'prepare', side_effect=partial
            ):
                with self.assertRaisesRegex(ValueError, 'fixture failure'):
                    entry.run(output, Path('unused-runtime'))
            self.assertEqual((output / 'source-manifest.json').read_bytes(), self.raw)
            binding = json.loads((output / 'intake-binding.json').read_text())
            self.assertEqual(binding['sourceManifestSha256'], entry.MANIFEST_SHA256)
            self.assertEqual(binding['eventHeadRevision'], 'b' * 40)
            self.assertEqual(set(binding['sourceFiles']), set(entry.SOURCE_FILES))
            self.assertFalse(binding['publicationApproval'])
            self.assertFalse(binding['gameCatalogueAdmission'])
            self.assertFalse(binding['listeningApproval'])


if __name__ == '__main__':
    unittest.main()
