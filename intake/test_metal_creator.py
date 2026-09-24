import copy
import unittest
from unittest.mock import patch
from prepare import (CREATOR_IDENTITIES, CREATOR_SOURCE_LIMITS, allowed_url,
                     allowed_redirect, validate_manifest, validate_source_page, collect_evidence)


class MetalCreatorIntakeTests(unittest.TestCase):
    def setUp(self):
        self.rows = [dict(r, status='rights-reviewed-listening-pending')
                     for u, r in CREATOR_IDENTITIES.items()
                     if u.endswith(('/the-dobermann/', '/folklore/'))]

    def test_two_exact_pending_metal_candidates(self):
        self.assertEqual({r['title'] for r in self.rows}, {'The Dobermann', 'Folklore'})
        validate_manifest({'format': 'revealline-core-intake.v1', 'tracks': self.rows})
        for row in self.rows:
            self.assertIs(row['contentId'], True)
            self.assertIs(row['recordingModeEligible'], False)
            self.assertEqual(row['family'], 'metal')
            self.assertEqual(CREATOR_SOURCE_LIMITS[row['source']], 16 * 1024 ** 2)

    def test_cross_pairs_and_changed_identity_or_approval_are_rejected(self):
        for i, row in enumerate(self.rows):
            for key, value in [('download', self.rows[1-i]['download']), ('family', 'ukrainian'),
                               ('contentId', False), ('recordingModeEligible', True), ('status', 'approved')]:
                changed = copy.deepcopy(row)
                changed[key] = value
                with self.assertRaises(ValueError):
                    validate_manifest({'format': 'revealline-core-intake.v1', 'tracks': [changed]})

    def test_no_host_wide_or_redirect_authority(self):
        for row in self.rows:
            for url in (row['source'], row['download']):
                self.assertTrue(allowed_url(url))
                for changed in (url + '?x=1', url + '#x', url.replace('https:', 'http:')):
                    self.assertFalse(allowed_url(changed))
                    self.assertFalse(allowed_redirect(url, changed))
            self.assertFalse(allowed_redirect(row['source'], row['download']))

    def test_exact_link_and_license_required(self):
        for row in self.rows:
            body = (f'<div data-src="{row["download"]}"></div>'
                    f'<a href="{row["licenseURL"]}">CC BY</a>').encode()
            validate_source_page(row, body)
            for broken in (body.replace(b'data-src', b'data-other'),
                           body.replace(row['licenseURL'].encode(), b'none')):
                with self.assertRaises(ValueError): validate_source_page(row, broken)

    def test_license_faq_and_content_id_retained(self):
        for row in self.rows:
            bodies = {row['source']: (f'<div data-src="{row["download"]}"></div>' + row['licenseURL']).encode(),
                      row['licensingInfo']: (row['licenseURL'] + ' Smart Content ID').encode(),
                      row['creatorFAQ']: b'FAQ'}
            def snapshot(url, output, pages): return bodies[url], {'url': url, 'sha256': 'fixture'}
            with patch('prepare.snapshot', side_effect=snapshot) as saved:
                self.assertEqual(len(collect_evidence(row, None, {}, {})), 3)
                self.assertEqual(saved.call_count, 3)
            bodies[row['licensingInfo']] = row['licenseURL'].encode()
            with patch('prepare.snapshot', side_effect=snapshot):
                with self.assertRaises(ValueError): collect_evidence(row, None, {}, {})


if __name__ == '__main__':
    unittest.main()
