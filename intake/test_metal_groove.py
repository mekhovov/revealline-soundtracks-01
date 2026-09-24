import copy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.request import Request

from prepare import (CREATOR_IDENTITIES, CREATOR_MAIN_TRACK_SOURCES,
                     CREATOR_SOURCE_LIMITS, IntakeRedirectHandler, allowed_url,
                     collect_evidence, validate_manifest, validate_source_page)


class MetalGrooveIntakeTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads(
            (Path(__file__).parent / 'metal-groove-audition-20260924.json').read_text())
        self.rows = self.manifest['tracks']

    @staticmethod
    def source(row):
        return (f'<div id="mainTrack" data-title="{row["title"]}" '
                f'data-src="{row["download"]}"></div>'
                f'<a href="{row["licenseURL"]}">CC BY 4.0</a>').encode()

    def test_active_core_manifest_exactly_matches_reviewed_four_track_batch(self):
        root = Path(__file__).parent
        active = (root / 'core-20260924.json').read_bytes()
        named = (root / 'metal-groove-audition-20260924.json').read_bytes()
        self.assertEqual(active, named)
        self.assertEqual(hashlib.sha256(active).hexdigest(),
                         '3a1e1e6fadc598c62f6bd98a1b7e5093a7e19f8101e880a8b2af9efcb6d3b3c7')
        self.assertEqual(json.loads(active)['batch'], 'metal-groove-audition-20260924')

    def test_four_exact_recordings_remain_pending_with_content_id(self):
        self.assertEqual({r['title'] for r in self.rows},
                         {'Anemo', 'Trial of Thorns', 'Riffs Two', 'Apocalypse'})
        self.assertEqual(len(self.rows), 4)
        self.assertIs(validate_manifest(self.manifest), self.manifest)
        for flag in ('publicationApproval', 'gameCatalogueAdmission', 'listeningApproval'):
            self.assertIs(self.manifest[flag], False)
        self.assertEqual({r['source'] for r in self.rows}, CREATOR_MAIN_TRACK_SOURCES)
        for row in self.rows:
            self.assertIs(row['contentId'], True)
            self.assertIs(row['recordingModeEligible'], False)
            self.assertIs(row['fullTrackListening'], False)
            self.assertEqual(row['instrumentalReview'], 'pending')
            self.assertEqual(row['gameplayReview'], 'pending')
            self.assertEqual(row['family'], 'metal')
            self.assertEqual(CREATOR_SOURCE_LIMITS[row['source']], 16 * 1024 ** 2)
            validate_source_page(row, self.source(row))

    def test_identity_license_style_and_approval_cannot_be_escalated(self):
        for row in self.rows:
            for key, value in (
                    ('id', row['id'] + '.alternate'), ('title', 'Different recording'),
                    ('artist', 'RevealLine'), ('artistURL', 'https://example.com'),
                    ('family', 'ukrainian'), ('license', 'CC0 1.0 Universal'),
                    ('licenseURL', 'https://creativecommons.org/publicdomain/zero/1.0/'),
                    ('licensingInfo', row['source']), ('creatorFAQ', row['source']),
                    ('contentId', False), ('contentId', 1),
                    ('recordingModeEligible', True), ('recordingModeEligible', 0),
                    ('status', 'approved'), ('fullTrackListening', True),
                    ('instrumentalReview', 'approved'), ('gameplayReview', 'approved')):
                changed = copy.deepcopy(row)
                changed[key] = value
                with self.subTest(title=row['title'], key=key, value=value):
                    with self.assertRaises(ValueError):
                        validate_manifest({'format': 'revealline-core-intake.v1',
                                           'tracks': [changed]})

    def test_allowed_recordings_cannot_be_cross_paired(self):
        for row in self.rows:
            for other in self.rows:
                if row is other:
                    continue
                changed = dict(row, download=other['download'])
                with self.assertRaises(ValueError):
                    validate_manifest({'format': 'revealline-core-intake.v1',
                                       'tracks': [changed]})

    def test_recommendation_links_do_not_establish_primary_identity(self):
        for row in self.rows:
            related = (f'<div class="track" data-title="{row["title"]}" '
                       f'data-src="{row["download"]}"></div>'
                       f'<a href="{row["licenseURL"]}">CC BY 4.0</a>').encode()
            wrong_main = (b'<div id="mainTrack" data-title="Another song" '
                          b'data-src="https://example.com/other.mp3"></div>')
            for source in (related, wrong_main + related):
                with self.assertRaisesRegex(ValueError, 'Primary creator player'):
                    validate_source_page(row, source)

    def test_ambiguous_or_changed_primary_player_is_rejected(self):
        for row in self.rows:
            good = self.source(row)
            for broken in (
                    good + good,
                    good.replace(b'id="mainTrack"', b'id="mainTrack" id="other"'),
                    good.replace(b'data-title=', b'data-title="Forged" data-title='),
                    good.replace(b'data-src=', b'data-src="https://example.com/x" data-src='),
                    good.replace(row['title'].encode(), b'Another title'),
                    good.replace(b'.mp3"', b'.mp3?changed=1"')):
                with self.assertRaisesRegex(ValueError, 'Primary creator player'):
                    validate_source_page(row, broken)

    def test_no_host_wide_url_or_cross_recording_redirect_authority(self):
        for row in self.rows:
            for original in (row['source'], row['download']):
                self.assertTrue(allowed_url(original))
                for changed in (original + '?download=1', original + '#fragment',
                                original.replace('https:', 'http:'),
                                original.replace('https://', 'https://u:p@'),
                                original.replace('.net/', '.net.evil.test/')):
                    if changed == original:
                        continue
                    self.assertFalse(allowed_url(changed))
                    with self.assertRaises(ValueError):
                        IntakeRedirectHandler(original).redirect_request(
                            Request(original), None, 302, 'Found', {}, changed)
                other = next(r for r in self.rows if r is not row)
                with self.assertRaises(ValueError):
                    IntakeRedirectHandler(original).redirect_request(
                        Request(original), None, 302, 'Found', {}, other['download'])

    def test_license_and_content_id_evidence_must_still_match(self):
        for row in self.rows:
            for licensing in (
                    (row['licenseURL'] + ' Smart Content ID').encode(),
                    row['licenseURL'].encode(),
                    b'Smart Content ID but no approved licence'):
                bodies = {row['source']: self.source(row),
                          row['licensingInfo']: licensing,
                          row['creatorFAQ']: b'Keep author and title credits.'}
                def snapshot(url, output, pages):
                    return bodies[url], {'url': url, 'sha256': 'fixture'}
                with patch('prepare.snapshot', side_effect=snapshot) as saved:
                    if licensing.startswith(row['licenseURL'].encode()) and b'Smart Content ID' in licensing:
                        evidence = collect_evidence(row, None, {}, {})
                        self.assertEqual(set(evidence),
                                         {'sourceSnapshot', 'licensingInfoSnapshot', 'creatorFAQSnapshot'})
                    else:
                        with self.assertRaises(ValueError):
                            collect_evidence(row, None, {}, {})
                    self.assertEqual(saved.call_count, 3)

    def test_changed_primary_stops_before_later_evidence_or_audio(self):
        row = self.rows[0]
        with patch('prepare.snapshot', return_value=(
                b'<a href="' + row['download'].encode() + b'">Related song</a>',
                {'url': row['source'], 'sha256': 'fixture'})) as saved:
            with patch('prepare.fetch') as network:
                with self.assertRaisesRegex(ValueError, 'Primary creator player'):
                    collect_evidence(row, None, {}, {})
                self.assertEqual(saved.call_count, 1)
                network.assert_not_called()


if __name__ == '__main__':
    unittest.main()
