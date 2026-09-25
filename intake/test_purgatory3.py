import copy
import hashlib
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

import itch_audio
import itch_source
import prepare
import prepare_purgatory3 as entry
import purgatory3_pins as pins
from test_itch_source import FixtureClient


DESCRIPTION = (
    '<div class="formatted_description user_formatted">'
    '<p>Reviewed fixture. License: CC By 4.0</p>'
    '<a href="https://creativecommons.org/licenses/by/4.0/">CC BY</a></div>'
)
DESCRIPTION_FACTS = {
    'text': 'Reviewed fixture. License: CC By 4.0 CC BY',
    'links': ['https://creativecommons.org/licenses/by/4.0/'],
}
DESCRIPTION_SHA = hashlib.sha256(
    json.dumps(
        DESCRIPTION_FACTS,
        ensure_ascii=False,
        sort_keys=True,
        separators=(',', ':'),
    ).encode()
).hexdigest()


def fixture(track_id):
    client = FixtureClient(track_id)
    client.page += DESCRIPTION
    return client


class Purgatory3Tests(unittest.TestCase):
    def setUp(self):
        self.raw = entry.MANIFEST.read_bytes()
        self.manifest = entry.checked_manifest(self.raw)
        self.rows = self.manifest['tracks']

    def test_exact_four_pending_metal_recordings(self):
        self.assertEqual({row['id'] for row in self.rows}, set(pins.UPLOAD_PINS))
        self.assertEqual(len(self.rows), 4)
        for flag in ('publicationApproval', 'gameCatalogueAdmission', 'listeningApproval'):
            self.assertIs(self.manifest[flag], False)
        for row in self.rows:
            self.assertEqual(row['family'], 'metal')
            self.assertEqual(row['license'], 'CC BY 4.0 International')
            self.assertEqual(row['contentId'], 'unknown')
            self.assertIs(row['recordingModeEligible'], False)
            self.assertIs(row['fullTrackListening'], False)
            self.assertEqual(row['instrumentalReview'], 'pending')
            self.assertEqual(row['gameplayReview'], 'pending')
            self.assertEqual(row['explicitContentReview'], 'pending')
            self.assertEqual(row['exactNativeDurationReview'], 'pending-hosted-decode')
            self.assertEqual(row['minimumDurationSeconds'], 100)

    def test_exact_source_uploads_and_tempo_order(self):
        observed = {
            'davidkbd.mutilations-melody': (3755088, 14549174),
            'davidkbd.bone-grinders-ballad': (3755088, 14549173),
            'davidkbd.the-slicing-strain': (3755088, 14549177),
            'davidkbd.visceral-vengeance': (3755088, 14549172),
        }
        self.assertEqual(set(observed), set(pins.UPLOAD_PINS))
        self.assertEqual(pins.DESCRIPTION_HASHES, {
            pins.SOURCE_KEY: 'fcab6f9052b1cc95f341fa5ccfdf1ea7c0275ce0bcf885559989ecd21137bd73'
        })
        for row in self.rows:
            self.assertEqual((row['gameId'], row['uploadId']), observed[row['id']])
            itch_audio.validate_row(row)

    def test_full_files_only_and_no_other_pack_tracks(self):
        names = [row['uploadName'] for row in self.rows]
        self.assertEqual(len(names), len(set(names)))
        self.assertTrue(all(name.endswith('.ogg') for name in names))
        self.assertFalse(any('mini loop' in name.lower() for name in names))
        excluded = ('Grave Rot Requiem', 'Blood Soaked Earth',
                    'Devoured by Darkness', 'Putrid Desecration')
        self.assertFalse(any(title in name for title in excluded for name in names))

    def test_all_exact_uploads_resolve_metadata_without_media_requests(self):
        with patch.dict(itch_source.DESCRIPTION_HASHES, {pins.SOURCE_KEY: DESCRIPTION_SHA}):
            for track_id in pins.UPLOAD_PINS:
                client = fixture(track_id)
                result = itch_source.resolve(track_id, client)
                self.assertEqual(len(client.requests), 5)
                self.assertTrue(all(url.startswith(client.source) for url, _ in client.requests))
                self.assertEqual(result.receipt()['uploadId'], client.upload)
                self.assertFalse(result.receipt()['audioAcquired'])
                self.assertFalse(result.receipt()['admitted'])

    def test_description_or_license_change_stops_before_download(self):
        key = 'davidkbd.bone-grinders-ballad'
        with patch.dict(itch_source.DESCRIPTION_HASHES, {pins.SOURCE_KEY: DESCRIPTION_SHA}):
            for changed in (
                DESCRIPTION.replace('Reviewed fixture.', 'Standalone redistribution prohibited.'),
                DESCRIPTION.replace('by/4.0/', 'by-nc/4.0/'),
                DESCRIPTION + DESCRIPTION,
                '',
            ):
                client = FixtureClient(key)
                client.page += changed
                with self.assertRaises(ValueError):
                    itch_source.resolve(key, client)
                self.assertEqual(len(client.requests), 1)

    def test_exact_native_hashes_are_absent_or_published_as_one_complete_batch(self):
        hashes, titles = prepare.public_recording_fingerprints(Path('.'))
        observations = {
            "Mutilation's Melody": '8975fcfc5594e83186eeb96efee5f02b5e915da72d3415e8f5832428fda0de59',
            "Bone Grinder's Ballad": 'e991b3c11b02843fce19677099d68a3eb692928d3287c91c3dbd16015a749cf2',
            'The Slicing Strain': '73cf3fc0151101f513af31f8528bc0aa4fa86e54319645646806b60e45ab042b',
            'Visceral Vengeance': 'e0fc2f888b2fe3b189140b46a59d25348f22a43fcbb673fc0a98d8db50c92c20',
        }
        native_published = []
        title_published = []
        for title, native_hash in observations.items():
            native_present = native_hash in hashes
            title_present = re.sub(r'[^a-z0-9]', '', title.lower()) in titles
            self.assertEqual(native_present, title_present)
            native_published.append(native_present)
            title_published.append(title_present)
        self.assertIn(native_published, ([False] * 4, [True] * 4))
        self.assertIn(title_published, ([False] * 4, [True] * 4))

    def test_manifest_is_immutable_and_local_acquisition_is_refused(self):
        changed = copy.deepcopy(self.manifest)
        changed['tracks'][0]['recordingModeEligible'] = True
        with self.assertRaisesRegex(ValueError, 'Immutable'):
            entry.checked_manifest(json.dumps(changed).encode())
        with patch.dict('os.environ', {}, clear=True), patch.object(entry, 'prepare') as acquire:
            with self.assertRaisesRegex(ValueError, 'distinct hosted'):
                entry.run(Path('unused-output'), Path('unused-runtime'))
            acquire.assert_not_called()

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
                + '@refs/pull/1/merge'
            ),
            'GITHUB_RUN_ID': '123',
        }

    def test_partial_failure_preserves_binding_without_success_claim(self):
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
            self.assertFalse(binding['publicationApproval'])
            self.assertFalse(binding['gameCatalogueAdmission'])
            self.assertFalse(binding['listeningApproval'])


if __name__ == '__main__':
    unittest.main()
