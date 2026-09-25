import copy
import hashlib
import html
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import prepare
import prepare_synth_third_directions as entry


class SynthThirdDirectionsTests(unittest.TestCase):
    def setUp(self):
        self.raw = entry.MANIFEST.read_bytes()
        self.manifest = entry.checked_manifest(self.raw)
        self.rows = self.manifest['tracks']

    def test_exact_four_track_audition_slate(self):
        self.assertEqual(
            [row['id'] for row in self.rows],
            ['bogart-vgm.90s-racer-techno', 'arold-valda.neon-pulse',
             'tcarisland.prismatic-light', 'zodik.future-travel'])
        for flag in ('publicationApproval', 'gameCatalogueAdmission',
                     'defaultPlaylistAdmission', 'recordingModeAdmission',
                     'listeningApproval'):
            self.assertIs(self.manifest[flag], False)
        for row in self.rows:
            self.assertEqual(row['family'], 'synth90s')
            self.assertEqual(row['status'], 'rights-reviewed-listening-pending')
            self.assertIs(row['auditionOnly'], True)
            self.assertIs(row['defaultPlaylistEligible'], False)
            self.assertIs(row['recordingModeEligible'], False)
            self.assertIs(row['fullTrackListening'], False)
            self.assertEqual(row['instrumentalReview'], 'pending')
            self.assertEqual(row['gameplayReview'], 'pending')
            self.assertEqual(row['explicitContentReview'], 'pending')
            self.assertEqual(row['exactNativeDurationReview'], 'pending-hosted-decode')

    def test_exact_source_mapping_and_rights_terms(self):
        expected = {
            'bogart-vgm.90s-racer-techno': (
                'https://opengameart.org/content/90s-racer-techno',
                'https://opengameart.org/sites/default/files/90s_racer_techno_0.mp3',
                6919579, 'da4d941c6abfc4aa4f44191fa27cb06afb80681e0af8c7eb5c1a32ff5c85605b',
                '.mp3', 'CC BY 4.0 International'),
            'arold-valda.neon-pulse': (
                'https://opengameart.org/content/neon-pulse',
                'https://opengameart.org/sites/default/files/neon_pulse.flac',
                22513720, '533aceb7e3f81f4f2a8a23527526334697d6d7c074d5711a447accf41b01fed7',
                '.flac', 'CC BY 4.0 International'),
            'tcarisland.prismatic-light': (
                'https://opengameart.org/content/prismatic-light',
                'https://opengameart.org/sites/default/files/prismaticlight_0.mp3',
                5511488, '2e0a45a3423ade454c50ba61fe82e8c7e912a22ab390887607e02458cec8b239',
                '.mp3', 'CC BY 4.0 International'),
            'zodik.future-travel': (
                'https://opengameart.org/content/zodik-future-travel',
                'https://opengameart.org/sites/default/files/Zodik%20-%20Future%20Travel_0.ogg',
                2045714, '10d7b71e7e48ce05f31fbfd820e6d669e6b7690b89fde9b199c25bbf07c2de92',
                '.ogg', 'CC BY 3.0 Unported'),
        }
        for row in self.rows:
            self.assertEqual(
                (row['source'], row['download'], row['expectedSourceBytes'],
                 row['expectedSourceSha256'], row['expectedSourceSuffix'], row['license']),
                expected[row['id']])
            self.assertGreaterEqual(len(row['requiredSourceTerms']), 1)
            self.assertIn(row['licenseURL'], row['credit'])
        bogart = self.rows[0]
        self.assertIn('https://www.facebook.com/BogartVGM/', bogart['credit'])
        neon = self.rows[1]
        self.assertIs(neon['contentId'], False)
        self.assertIs(neon['recordingModeEligible'], False)
        self.assertEqual(self.rows[2]['publishedBpm'], 140)

    def test_exact_native_hashes_are_not_in_public_catalogue(self):
        known_hashes, known_titles = prepare.public_recording_fingerprints()
        for row in self.rows:
            self.assertNotIn(row['expectedSourceSha256'], known_hashes)
            normalized = ''.join(char for char in row['title'].lower() if char.isalnum())
            self.assertNotIn(normalized, known_titles)

    def test_source_page_binds_download_licence_and_required_terms(self):
        for row in self.rows:
            body = ('<html><a href="' + row['download'] + '">recording</a>'
                    '<a href="' + row['licenseURL'] + '">licence</a>'
                    + ''.join(html.escape(term) for term in row['requiredSourceTerms'])
                    + '</html>').encode()
            prepare.validate_source_page(row, body)
            with self.assertRaisesRegex(ValueError, 'rights evidence'):
                prepare.validate_source_page(row, body.replace(
                    html.escape(row['requiredSourceTerms'][0]).encode(), b'changed', 1))

    def test_source_bytes_are_bound_before_decode(self):
        for row in self.rows:
            body = b'x' * row['expectedSourceBytes']
            changed = dict(row, expectedSourceSha256=hashlib.sha256(body).hexdigest())
            prepare.validate_source_identity(
                changed, body, row['download'], row['expectedSourceSuffix'])
            for mutation in (
                    ('body', body + b'x'),
                    ('url', row['download'] + '?changed=1'),
                    ('suffix', '.mp3' if row['expectedSourceSuffix'] != '.mp3' else '.ogg')):
                with self.subTest(id=row['id'], mutation=mutation[0]), \
                        self.assertRaisesRegex(ValueError, 'exact source identity'):
                    prepare.validate_source_identity(
                        changed,
                        mutation[1] if mutation[0] == 'body' else body,
                        mutation[1] if mutation[0] == 'url' else row['download'],
                        mutation[1] if mutation[0] == 'suffix' else row['expectedSourceSuffix'])

    def test_invalid_source_pins_and_rights_terms_are_rejected(self):
        for key, value in (
                ('expectedSourceSha256', '0' * 63),
                ('expectedSourceBytes', 0),
                ('expectedSourceSuffix', '.wav'),
                ('requiredSourceTerms', []),
                ('requiredSourceTerms', ['x' * 241])):
            changed = copy.deepcopy(self.manifest)
            changed['tracks'][0][key] = value
            if key == 'requiredSourceTerms' and value == []:
                # Empty is valid for historical rows; malformed type is not.
                changed['tracks'][0][key] = 'not-a-list'
            with self.subTest(field=key, value=value), self.assertRaises(ValueError):
                prepare.validate_manifest(changed)

    def test_manifest_is_immutable_and_local_acquisition_is_refused(self):
        changed = copy.deepcopy(self.manifest)
        changed['tracks'][0]['recordingModeEligible'] = True
        with self.assertRaisesRegex(ValueError, 'Immutable'):
            entry.checked_manifest(json.dumps(changed).encode())
        with tempfile.TemporaryDirectory() as directory, \
                patch.dict('os.environ', {}, clear=True), \
                patch.object(entry, 'prepare') as acquire:
            with self.assertRaisesRegex(ValueError, 'distinct hosted'):
                entry.run(Path(directory) / 'output', Path('unused-runtime'))
            acquire.assert_not_called()


if __name__ == '__main__':
    unittest.main()
