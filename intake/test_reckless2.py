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
import assemble_reckless2 as publication
import prepare_reckless2 as entry
import reckless2_pins as pins
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
    json.dumps(DESCRIPTION_FACTS, ensure_ascii=False, sort_keys=True,
               separators=(',', ':')).encode()
).hexdigest()


def fixture(track_id):
    client = FixtureClient(track_id)
    client.page += DESCRIPTION
    return client


class Reckless2Tests(unittest.TestCase):
    def setUp(self):
        self.raw = entry.MANIFEST.read_bytes()
        self.manifest = entry.checked_manifest(self.raw)
        self.rows = self.manifest['tracks']

    def test_exact_four_pending_high_energy_recordings(self):
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
            self.assertEqual(row['gameplayReview'], 'pending')
            self.assertEqual(row['explicitContentReview'], 'pending')
            self.assertEqual(row['exactNativeDurationReview'], 'pending-hosted-decode')
            self.assertGreaterEqual(row['tempoBpm'], 166)

    def test_exact_source_uploads(self):
        observed = {
            'davidkbd.city-limits-crash': (3681796, 14147896),
            'davidkbd.edge-of-the-city': (3681796, 14147899),
            'davidkbd.defiant-descent': (3681796, 14147898),
            'davidkbd.airborne-anarchy': (3681796, 14147903),
        }
        self.assertEqual(set(observed), set(pins.UPLOAD_PINS))
        self.assertEqual(pins.DESCRIPTION_HASHES, {
            pins.SOURCE_KEY: '29f7786b366726e296cb8b36841897e8bdbc3be9b4561cf95c514cbc9facba0b'
        })
        for row in self.rows:
            self.assertEqual((row['gameId'], row['uploadId']), observed[row['id']])
            itch_audio.validate_row(row)

    def test_full_files_only_and_paid_archives_excluded(self):
        names = [row['uploadName'] for row in self.rows]
        self.assertEqual(len(names), len(set(names)))
        self.assertTrue(all(name.endswith('.ogg') for name in names))
        self.assertFalse(any('.zip' in name.lower() or '.wav' in name.lower() for name in names))

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
        key = 'davidkbd.city-limits-crash'
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

    def test_current_public_catalogue_has_no_title_duplicates(self):
        baseline = json.loads(publication.merged_catalogue_bytes())
        baseline_titles = {
            re.sub(r'[^a-z0-9]', '', row['title'].lower())
            for row in baseline['tracks']
        }
        for title in pins.REFERENCE_LOOP_END_SECONDS:
            expected = pins.UPLOAD_PINS[title][3]
            self.assertNotIn(
                re.sub(r'[^a-z0-9]', '', expected.lower()), baseline_titles
            )

        current = json.loads(Path('catalogue.json').read_bytes())
        self.assertGreaterEqual(len(current['tracks']), len(baseline['tracks']))
        self.assertEqual(
            current['tracks'][:len(baseline['tracks'])], baseline['tracks']
        )
        current_titles = [
            re.sub(r'[^a-z0-9]', '', row['title'].lower())
            for row in current['tracks']
        ]
        self.assertEqual(len(current_titles), len(set(current_titles)))

    def test_reference_loop_end_is_not_claimed_as_exact_duration(self):
        for row in self.rows:
            self.assertEqual(
                row['referenceLoopEndSeconds'],
                pins.REFERENCE_LOOP_END_SECONDS[row['id']],
            )
            self.assertEqual(row['referenceLoopSource'], pins.SOURCE)
            self.assertNotIn('referenceDurationSeconds', row)
            self.assertEqual(row['exactNativeDurationReview'], 'pending-hosted-decode')

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
                'mekhovov/revealline-soundtracks-01/' + entry.WORKFLOW + '@refs/heads/test'
            ),
            'GITHUB_RUN_ID': '123',
        }

    def test_partial_failure_preserves_binding_without_success_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'evidence'

            def partial(_manifest, destination, _runtime):
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
