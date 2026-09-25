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

    def test_exact_native_hashes_are_absent_or_published_as_one_complete_batch(self):
        known_hashes, known_titles = prepare.public_recording_fingerprints()
        published = []
        for row in self.rows:
            normalized = ''.join(char for char in row['title'].lower() if char.isalnum())
            native_present = row['expectedSourceSha256'] in known_hashes
            title_present = normalized in known_titles
            self.assertEqual(native_present, title_present)
            published.append(native_present)
        self.assertIn(published, ([False] * 4, [True] * 4))

    def test_source_page_binds_download_and_licence(self):
        for row in self.rows:
            body = ('<html><a href="' + row['download'] + '">recording</a>'
                    '<a href="' + row['licenseURL'] + '">licence</a>'
                    + ''.join(html.escape(term) for term in row['requiredSourceTerms'])
                    + '</html>').encode()
            prepare.validate_source_page(row, body)

    def test_prepared_bytes_and_rights_evidence_are_bound_to_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            for name in ('originals', 'objects', 'evidence'):
                (output / name).mkdir()
            manifest = copy.deepcopy(self.manifest)
            tracks = []
            for index, row in enumerate(manifest['tracks']):
                original_bytes = f'native-{index}'.encode()
                row['expectedSourceBytes'] = len(original_bytes)
                row['expectedSourceSha256'] = hashlib.sha256(original_bytes).hexdigest()
                original_path = ('originals/' + row['expectedSourceSha256']
                                 + row['expectedSourceSuffix'])
                (output / original_path).write_bytes(original_bytes)

                evidence = ('<a href="' + row['licenseURL'] + '">licence</a>'
                            + ''.join(html.escape(term)
                                      for term in row['requiredSourceTerms'])).encode()
                evidence_sha = hashlib.sha256(evidence).hexdigest()
                evidence_path = 'evidence/' + evidence_sha + '.html'
                (output / evidence_path).write_bytes(evidence)

                derivative = f'derivative-{index}'.encode()
                derivative_sha = hashlib.sha256(derivative).hexdigest()
                derivative_path = 'objects/' + derivative_sha + '.mp3'
                (output / derivative_path).write_bytes(derivative)
                tracks.append({
                    'id': row['id'],
                    'completeDecode': True,
                    'original': {'path': original_path,
                                 'sha256': row['expectedSourceSha256'],
                                 'bytes': len(original_bytes), 'url': row['download']},
                    'sourceSnapshot': {'path': evidence_path, 'sha256': evidence_sha,
                                       'url': row['source']},
                    'delivery': {'path': derivative_path, 'sha256': derivative_sha,
                                 'bytes': len(derivative)},
                })
            receipt = {'tracks': tracks, 'failures': []}
            (output / 'receipt.json').write_text(json.dumps(receipt))
            entry.validate_prepared_intake(manifest, output)

            first = tracks[0]
            original = output / first['original']['path']
            original.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'native source bytes'):
                entry.validate_prepared_intake(manifest, output)
            original.write_bytes(b'native-0')

            evidence = output / first['sourceSnapshot']['path']
            evidence.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'snapshot bytes'):
                entry.validate_prepared_intake(manifest, output)

    def test_invalid_source_pins_and_rights_terms_are_rejected(self):
        for key, value in (
                ('expectedSourceSha256', '0' * 63),
                ('expectedSourceBytes', 0),
                ('expectedSourceSuffix', '.wav'),
                ('requiredSourceTerms', []),
                ('requiredSourceTerms', ['x' * 241])):
            changed = copy.deepcopy(self.manifest)
            changed['tracks'][0][key] = value
            with self.subTest(field=key, value=value), self.assertRaises(ValueError):
                entry.validate_third_manifest(changed)
        changed = copy.deepcopy(self.manifest)
        changed['recordingModeAdmission'] = True
        with self.assertRaisesRegex(ValueError, 'admission or approval'):
            entry.validate_third_manifest(changed)

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
