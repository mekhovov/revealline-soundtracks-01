import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import itch_audio
import itch_source
import prepare_second_directions as entry
import second_directions_pins as pins
from test_itch_source import FixtureClient, signed


DESCRIPTION = ('<div class="formatted_description user_formatted">'
               '<p>Reviewed fixture. License: CC By 4.0</p>'
               '<a href="https://creativecommons.org/licenses/by/4.0/">CC BY</a></div>')
DESCRIPTION_FACTS = {
    'text': 'Reviewed fixture. License: CC By 4.0 CC BY',
    'links': ['https://creativecommons.org/licenses/by/4.0/'],
}
DESCRIPTION_SHA = hashlib.sha256(json.dumps(
    DESCRIPTION_FACTS, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def fixture(track_id):
    client = FixtureClient(track_id)
    client.page += DESCRIPTION
    return client


class SecondDirectionsTests(unittest.TestCase):
    def setUp(self):
        self.raw = entry.MANIFEST.read_bytes()
        self.manifest = entry.checked_manifest(self.raw)
        self.rows = self.manifest['tracks']

    def test_exact_twelve_pending_six_six_slate(self):
        self.assertEqual(len(self.rows), 12)
        self.assertEqual({row['id'] for row in self.rows},
                         set(pins.UPLOAD_PINS) | {'bogart-vgm.neon-action-full'})
        self.assertEqual([row['family'] for row in self.rows].count('synth90s'), 6)
        self.assertEqual([row['family'] for row in self.rows].count('metal'), 6)
        for flag in ('publicationApproval', 'gameCatalogueAdmission', 'listeningApproval'):
            self.assertIs(self.manifest[flag], False)
        for row in self.rows:
            self.assertEqual(row['license'], 'CC BY 4.0 International')
            self.assertEqual(row['contentId'], 'unknown')
            self.assertIs(row['recordingModeEligible'], False)
            self.assertIs(row['fullTrackListening'], False)
            self.assertEqual(row['instrumentalReview'], 'pending')
            self.assertEqual(row['gameplayReview'], 'pending')
            self.assertEqual(row['explicitContentReview'], 'pending')
            self.assertEqual(row['exactNativeDurationReview'], 'pending-hosted-decode')
            self.assertEqual(row['minimumDurationSeconds'], 180)
            if 'referenceDurationSeconds' in row:
                self.assertGreaterEqual(row['referenceDurationSeconds'], 180)
                self.assertLessEqual(row['referenceDurationSeconds'], 360)

    def test_exact_source_and_upload_observations(self):
        observed = {
            'davidkbd.cyber-lights': (2187961, 8382058),
            'davidkbd.neon-arcadia-awakening': (2187961, 8382061),
            'davidkbd.time-warp': (2187961, 8382063),
            'davidkbd.quantum-ripples-of-sound': (2187961, 8382067),
            'davidkbd.synthetic-power-surge': (2187961, 8382551),
            'davidkbd.solar-storm': (2445174, 13507642),
            'davidkbd.galactic-battle': (2445174, 13507638),
            'davidkbd.orbital-assault': (2445174, 13507646),
            'davidkbd.they-want-death': (2246806, 12451195),
            'davidkbd.cosmic-clash': (2445174, 13507640),
            'davidkbd.sin-their-pity-their-agony': (2246806, 12451194),
        }
        self.assertEqual(set(observed), set(pins.UPLOAD_PINS))
        self.assertEqual(set(pins.DESCRIPTION_HASHES), set(pins.SOURCE_PINS))
        self.assertEqual(len(set(pins.DESCRIPTION_HASHES.values())), 3)
        for row in (row for row in self.rows if row.get('acquisition') ==
                    'itch-public-free-download'):
            self.assertEqual((row['gameId'], row['uploadId']), observed[row['id']])
            itch_audio.validate_row(row)

    def test_distinct_compositions_exclude_alternates_and_short_cues(self):
        names = [row.get('uploadName', row.get('download')) for row in self.rows]
        self.assertEqual(len(names), len(set(names)))
        self.assertFalse(any(token in name.lower() for name in names
                             for token in ('short', 'miniloop', 'cinematic', 'you win', 'you loss')))
        self.assertFalse(any('variation' in name.lower() for name in names))
        synth_uploads = [name for name in names if 'Electric Pulse -' in name]
        self.assertEqual(len(synth_uploads), 5)
        self.assertTrue(all(name.endswith('-full.ogg') for name in synth_uploads))

    def test_all_exact_uploads_resolve_metadata_without_media_requests(self):
        with patch.dict(itch_source.DESCRIPTION_HASHES,
                        {source: DESCRIPTION_SHA for source in pins.SOURCE_PINS}):
            for track_id in pins.UPLOAD_PINS:
                client = fixture(track_id)
                result = itch_source.resolve(track_id, client)
                self.assertEqual(len(client.requests), 5)
                self.assertTrue(all(url.startswith(client.source) for url, _ in client.requests))
                self.assertEqual(result.receipt()['uploadId'], client.upload)
                self.assertFalse(result.receipt()['audioAcquired'])
                self.assertFalse(result.receipt()['admitted'])

    def test_description_or_license_change_stops_before_free_download(self):
        key = 'davidkbd.cyber-lights'
        with patch.dict(itch_source.DESCRIPTION_HASHES,
                        {'davidkbd-electric-pulse': DESCRIPTION_SHA}):
            for changed in (
                    DESCRIPTION.replace('Reviewed fixture.', 'Standalone redistribution prohibited.'),
                    DESCRIPTION.replace('by/4.0/', 'by-nc/4.0/'),
                    DESCRIPTION.replace('CC By 4.0', 'CC By 3.0'),
                    DESCRIPTION + DESCRIPTION,
                    DESCRIPTION.replace('</div>', ''), ''):
                client = FixtureClient(key)
                client.page += changed
                with self.assertRaises(ValueError):
                    itch_source.resolve(key, client)
                self.assertEqual(len(client.requests), 1)

    def test_identity_and_license_cross_pairing_rejected(self):
        rows = [row for row in self.rows if row.get('acquisition') ==
                'itch-public-free-download']
        for row in rows:
            other = next(candidate for candidate in rows if candidate['id'] != row['id'])
            with self.assertRaises(ValueError):
                itch_audio.validate_row(dict(row, uploadId=other['uploadId'],
                                             uploadName=other['uploadName']))
            for key, value in [('gameId', row['gameId'] + 1),
                               ('licenseURL', 'https://example.org'),
                               ('contentId', False), ('recordingModeEligible', True),
                               ('fullTrackListening', True), ('vocalContent', 'instrumental'),
                               ('exactNativeDurationReview', 'approved'),
                               ('minimumDurationSeconds', 60)]:
                with self.subTest(id=row['id'], field=key), self.assertRaises(ValueError):
                    itch_audio.validate_row(dict(row, **{key: value}))

    def test_cross_pack_response_rejected(self):
        with patch.dict(itch_source.DESCRIPTION_HASHES,
                        {source: DESCRIPTION_SHA for source in pins.SOURCE_PINS}):
            rows = [row for row in self.rows if row.get('acquisition') ==
                    'itch-public-free-download']
            for row in rows:
                client = fixture(row['id'])
                other = next(candidate for candidate in rows
                             if candidate['gameId'] != row['gameId'])
                client.result = {'url': signed(other['gameId'], other['uploadId']),
                                 'external': False}
                with self.assertRaisesRegex(ValueError, 'upload binding'):
                    itch_source.resolve(row['id'], client)

    def test_holds_are_not_registered_or_requested(self):
        held = ('davidkbd.see-you-in-hell', 'davidkbd.the-eternal-fight',
                'davidkbd.mach-overdrive', 'davidkbd.turbo-power-metal',
                'davidkbd.turbo-electro-metal', 'davidkbd.turbo-black-metal-instrumental',
                'davidkbd.pink-bloom', 'davidkbd.to-the-unknown',
                'davidkbd.lightyear-city', 'davidkbd.hexapuppies',
                'davidkbd.the-great-machine', 'davidkbd.disaster',
                'davidkbd.keep-my-rhythm-if-you-can', 'davidkbd.dangerous-and-bored',
                'davidkbd.speedy-and-hostile', 'davidkbd.purgatory',
                'davidkbd.on-fire', 'davidkbd.hades',
                'davidkbd.insanity-is-your-flame')
        for key in held:
            client = Mock()
            with self.assertRaises(ValueError):
                itch_source.resolve(key, client)
            client.read.assert_not_called()

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
        return {'GITHUB_ACTIONS': 'true',
                'GITHUB_REPOSITORY': 'mekhovov/revealline-soundtracks-01',
                'GITHUB_SHA': 'a' * 40, 'EVENT_HEAD_SHA': 'b' * 40,
                'GITHUB_WORKFLOW_REF':
                    'mekhovov/revealline-soundtracks-01/' + entry.WORKFLOW + '@refs/pull/1/merge',
                'GITHUB_RUN_ID': '123'}

    def test_partial_failure_preserves_exact_binding_without_success_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'evidence'

            def partial(manifest, destination, runtime):
                destination.mkdir()
                (destination / 'receipt.json').write_text('{"failures":[{"error":"fixture"}]}')
                raise ValueError('fixture failure')

            with patch.dict('os.environ', self.hosted_env(), clear=True), \
                    patch.object(entry, 'prepare', side_effect=partial):
                with self.assertRaisesRegex(ValueError, 'fixture failure'):
                    entry.run(output, Path('unused-runtime'))
            self.assertEqual((output / 'source-manifest.json').read_bytes(), self.raw)
            binding = json.loads((output / 'intake-binding.json').read_text())
            self.assertEqual(binding['sourceManifestSha256'], entry.MANIFEST_SHA256)
            self.assertEqual(binding['eventHeadRevision'], 'b' * 40)
            self.assertFalse(binding['publicationApproval'])
            self.assertFalse(binding['gameCatalogueAdmission'])
            self.assertFalse(binding['listeningApproval'])


if __name__ == '__main__':
    unittest.main()
