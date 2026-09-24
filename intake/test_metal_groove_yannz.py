import hashlib
import json
from pathlib import Path
import unittest

from prepare import validate_manifest, validate_source_page


class MetalGrooveYannzIntakeTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).parent
        self.active = (root / 'core-20260924.json').read_bytes()
        self.named = (root / 'metal-groove-yannz-audition-20260924.json').read_bytes()
        self.manifest = json.loads(self.named)
        self.rows = self.manifest['tracks']

    @staticmethod
    def source(row):
        return (f'<a href="{row["download"]}">Exact recording</a>'
                f'<a href="{row["licenseURL"]}">Published licence</a>').encode()

    def test_active_manifest_exactly_matches_named_five_track_batch(self):
        self.assertEqual(self.active, self.named)
        self.assertEqual(hashlib.sha256(self.active).hexdigest(),
                         '46098246897c753a96d32c5991c05119f1538beb434e38b17d39c49f622ceaae')
        self.assertEqual(self.manifest['batch'], 'metal-groove-yannz-audition-20260924')

    def test_five_exact_recordings_remain_pending(self):
        self.assertEqual({row['title'] for row in self.rows}, {
            'Pixel Damnation', "Revenge's Waiting", 'Soul Ripper',
            'German Industrial Metal', 'Achilles'})
        self.assertEqual(len(self.rows), 5)
        self.assertIs(validate_manifest(self.manifest), self.manifest)
        for flag in ('publicationApproval', 'gameCatalogueAdmission', 'listeningApproval'):
            self.assertIs(self.manifest[flag], False)
        for row in self.rows:
            self.assertIsNone(row['contentId'])
            self.assertIs(row['recordingModeEligible'], False)
            self.assertIs(row['fullTrackListening'], False)
            self.assertEqual(row['instrumentalReview'], 'pending')
            self.assertEqual(row['gameplayReview'], 'pending')
            self.assertEqual(row['family'], 'metal')
            validate_source_page(row, self.source(row))

    def test_short_boss_loop_does_not_claim_full_gameplay_role(self):
        revenge = next(row for row in self.rows if row['id'] == 'yannz.revenges-waiting')
        self.assertEqual(revenge['role'], 'boss-cue')
        self.assertEqual(revenge['publishedDuration'], '0:48')
        self.assertEqual(revenge['publishedMeter'], '12/8')
        self.assertNotEqual(revenge['role'], 'gameplay')


if __name__ == '__main__':
    unittest.main()
