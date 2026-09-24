import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import approved_directions_pins as pins
import itch_audio
import itch_source
import prepare_approved_directions as entry
from test_itch_source import FixtureClient, signed


ROOT = Path(__file__).parent
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


class ApprovedDirectionsTests(unittest.TestCase):
    def setUp(self):
        self.raw = entry.MANIFEST.read_bytes()
        self.manifest = entry.checked_manifest(self.raw)
        self.rows = self.manifest['tracks']

    def test_exact_twelve_slate_and_pending_six_six_split(self):
        self.assertEqual(len(self.rows), 12)
        self.assertEqual([r['family'] for r in self.rows].count('synth90s'), 6)
        self.assertEqual([r['family'] for r in self.rows].count('metal'), 6)
        self.assertEqual({r['id'] for r in self.rows},
                         {'bogart-vgm.retroracing-nightlife', *pins.UPLOAD_PINS})
        for flag in ('publicationApproval', 'gameCatalogueAdmission', 'listeningApproval'):
            self.assertIs(self.manifest[flag], False)
        for row in self.rows:
            self.assertEqual(row['licenseURL'], itch_source.LICENSE_URL)
            self.assertEqual(row['contentId'], 'unknown')
            self.assertIs(row['recordingModeEligible'], False)
            self.assertIs(row['fullTrackListening'], False)
            self.assertEqual(row['gameplayReview'], 'pending')
            self.assertEqual(row['explicitContentReview'], 'pending')

    def test_source_pins_are_exact_independent_anonymous_observations(self):
        observed = {
            'davidkbd.electric-pulse': (2187961, 8382056),
            'davidkbd.retrochrome-nights': (2187961, 8382060),
            'davidkbd.vapor-trails-pursuit': (2187961, 8382528),
            'davidkbd.electric-dreams-of-infinity': (2187961, 8382065),
            'davidkbd.digital-horizon': (2187961, 8382053),
            'davidkbd.plasma-storm': (1704727, 6501647),
            'davidkbd.meteor-shower': (2445174, 13507636),
            'davidkbd.urban-hairbanger': (1182848, 4397475),
            'davidkbd.grave-rot-requiem': (3755088, 14549171),
            'davidkbd.devoured-by-darkness': (3755088, 14549176),
            'davidkbd.tear-their-fate': (2246806, 12451192),
        }
        self.assertEqual(set(pins.UPLOAD_PINS), set(observed))
        for row in self.rows[1:]:
            self.assertEqual((row['gameId'], row['uploadId']), observed[row['id']])
            itch_audio.validate_row(row)
        self.assertEqual(set(pins.DESCRIPTION_HASHES), set(pins.SOURCE_PINS))
        self.assertEqual(len(set(pins.DESCRIPTION_HASHES.values())), 6)
        self.assertTrue(all(len(v) == 64 for v in pins.DESCRIPTION_HASHES.values()))

    def test_only_full_ogg_and_free_vocal_variants(self):
        for row in self.rows[1:6]:
            self.assertTrue(row['uploadName'].endswith('-full.ogg'))
        vocal = self.rows[-1]
        self.assertEqual(vocal['uploadName'],
                         'DavidKBD - Purgatory Pack vol2 - 01 - Tear their fate.ogg')
        self.assertEqual(vocal['vocalContent'], 'creator-described-vocals')
        self.assertEqual(vocal['instrumentalReview'], 'pending')
        self.assertNotIn('instrumental', vocal['uploadName'])
        for key in ('davidkbd.city-limits-crash', 'wekont.runner2088', 'davidkbd.street-beat'):
            client = Mock()
            with self.assertRaises(ValueError):
                itch_source.resolve(key, client)
            client.read.assert_not_called()

    def test_oga_pair_credit_and_hash_bound_entry(self):
        row = self.rows[0]
        self.assertEqual(row['source'], 'https://opengameart.org/content/retroracing-nightlife')
        self.assertEqual(row['download'],
                         'https://opengameart.org/sites/default/files/Retroracing%20Nightlife_0.mp3')
        self.assertIn('https://www.facebook.com/BogartVGM/', row['credit'])
        for key, value in [('download', row['download'].replace('Nightlife', 'Other')),
                           ('licenseURL', 'https://creativecommons.org/licenses/by-nc/4.0/'),
                           ('recordingModeEligible', True), ('contentId', False)]:
            changed = copy.deepcopy(self.manifest)
            changed['tracks'][0][key] = value
            with self.assertRaisesRegex(ValueError, 'Immutable'):
                entry.checked_manifest(json.dumps(changed).encode())
        with self.assertRaisesRegex(ValueError, 'Immutable'):
            entry.checked_manifest(self.raw + b' ')

    def test_all_new_exact_uploads_resolve_without_any_media_request(self):
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

    def test_source_terms_change_fails_before_free_download(self):
        key = 'davidkbd.electric-pulse'
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

    def test_normalization_ignores_session_and_whitespace_not_added_terms_or_links(self):
        self.assertEqual(itch_source.SourceDescription(DESCRIPTION).digest(), DESCRIPTION_SHA)
        changed = '<meta name="csrf_token" value="different">' + DESCRIPTION.replace('fixture.', 'fixture.\n\t')
        self.assertEqual(itch_source.SourceDescription(changed).digest(), DESCRIPTION_SHA)
        changed = DESCRIPTION.replace('</div>', '<p>New restriction</p></div>')
        self.assertNotEqual(itch_source.SourceDescription(changed).digest(), DESCRIPTION_SHA)
        changed = DESCRIPTION.replace('</div>', '<a href="https://example.org/terms">Terms</a></div>')
        self.assertNotEqual(itch_source.SourceDescription(changed).digest(), DESCRIPTION_SHA)

    def test_identity_and_licence_cross_pairing_rejected_for_every_new_recording(self):
        for row in self.rows[1:]:
            for other in self.rows[1:]:
                if row is other:
                    continue
                changed = dict(row, uploadId=other['uploadId'], uploadName=other['uploadName'])
                with self.subTest(id=row['id'], other=other['id']), self.assertRaises(ValueError):
                    itch_audio.validate_row(changed)
            for key, value in [('gameId', row['gameId'] + 1), ('licenseURL', 'https://example.org'),
                               ('license', 'CC0'), ('contentId', False),
                               ('recordingModeEligible', True), ('vocalContent', 'instrumental'),
                               ('instrumentalReview', 'approved'), ('fullTrackListening', True)]:
                with self.subTest(id=row['id'], field=key), self.assertRaises(ValueError):
                    itch_audio.validate_row(dict(row, **{key: value}))

    def test_cross_pack_download_response_rejected_even_for_other_registered_upload(self):
        with patch.dict(itch_source.DESCRIPTION_HASHES,
                        {source: DESCRIPTION_SHA for source in pins.SOURCE_PINS}):
            for row in self.rows[1:]:
                client = fixture(row['id'])
                other = self.rows[6] if row['id'] != self.rows[6]['id'] else self.rows[1]
                client.result = {'url': signed(other['gameId'], other['uploadId']), 'external': False}
                with self.assertRaisesRegex(ValueError, 'upload binding'):
                    itch_source.resolve(row['id'], client)

    def test_paid_short_or_instrumental_name_stops_before_file_endpoint(self):
        key = 'davidkbd.electric-pulse'
        with patch.dict(itch_source.DESCRIPTION_HASHES,
                        {'davidkbd-electric-pulse': DESCRIPTION_SHA}):
            for value in ('DavidKBD - Electric Pulse - 01 - Electric Pulse-sort.ogg',
                          'DavidKBD - Electric Pulse Pack WAVE Files.zip', 'Other.ogg'):
                client = fixture(key)
                client.uploads = client.uploads.replace(client.name, value)
                with self.assertRaisesRegex(ValueError, 'upload identity'):
                    itch_source.resolve(key, client)
                self.assertEqual(len(client.requests), 4)

    def test_no_local_acquisition_or_overwriting_existing_evidence(self):
        with patch.dict('os.environ', {}, clear=True), patch.object(entry, 'prepare') as acquire:
            with self.assertRaisesRegex(ValueError, 'distinct hosted'):
                entry.run(Path('unused-output'), Path('unused-runtime'))
            acquire.assert_not_called()
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict('os.environ', self.hosted_env(), clear=True), patch.object(entry, 'prepare') as acquire:
                with self.assertRaisesRegex(ValueError, 'fresh output'):
                    entry.run(Path(directory), Path('unused-runtime'))
                acquire.assert_not_called()

    @staticmethod
    def hosted_env():
        return {'GITHUB_ACTIONS': 'true', 'GITHUB_REPOSITORY': 'mekhovov/revealline-soundtracks-01',
                'GITHUB_SHA': 'a' * 40, 'EVENT_HEAD_SHA': 'b' * 40,
                'GITHUB_WORKFLOW_REF': 'mekhovov/revealline-soundtracks-01/' + entry.WORKFLOW + '@refs/pull/1/merge',
                'GITHUB_RUN_ID': '123'}

    def test_partial_failure_preserves_exact_source_binding_without_success_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'evidence'
            def partial(manifest, destination, runtime):
                destination.mkdir()
                (destination / 'receipt.json').write_text('{"failures":[{"error":"fixture"}]}')
                raise ValueError('fixture failure')
            with patch.dict('os.environ', self.hosted_env(), clear=True), patch.object(entry, 'prepare', side_effect=partial):
                with self.assertRaisesRegex(ValueError, 'fixture failure'):
                    entry.run(output, Path('unused-runtime'))
            self.assertEqual((output / 'source-manifest.json').read_bytes(), self.raw)
            binding = json.loads((output / 'intake-binding.json').read_text())
            self.assertEqual(binding['sourceManifestSha256'], entry.MANIFEST_SHA256)
            self.assertEqual(binding['eventHeadRevision'], 'b' * 40)
            self.assertFalse(binding['publicationApproval'])
            self.assertFalse(binding['gameCatalogueAdmission'])
            self.assertFalse(binding['listeningApproval'])
            self.assertEqual(json.loads((output / 'receipt.json').read_text())['failures'][0]['error'], 'fixture')


if __name__ == '__main__':
    unittest.main()
