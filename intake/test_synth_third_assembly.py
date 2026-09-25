import copy
import unittest
from unittest.mock import patch

import assemble_approved_directions as assembler
import assemble_synth_third_directions as subject


class SynthThirdAssemblyConfigurationTests(unittest.TestCase):
    def test_exact_artifact_source_runner_and_permanent_tree_proof(self):
        self.assertEqual(subject.CONFIG['RUN'], 36082136561)
        self.assertEqual(subject.CONFIG['ARTIFACT'], 10843185196)
        self.assertEqual(subject.CONFIG['ZIP_BYTES'], 62234070)
        self.assertEqual(
            subject.CONFIG['ZIP_SHA'],
            'fdcf01c091d53b7349d873569cb4fe4ba1e365432f52fd51f98938feb6d96ecc',
        )
        self.assertEqual(subject.CONFIG['SOURCE_HEAD'], '400367c644cafeae6e8ce94011cbb790561455f6')
        self.assertEqual(subject.CONFIG['RUNNER'], 'e774748eace8567fbeda3d8c8e31245a29dfbb9b')
        self.assertEqual(subject.CONFIG['TREE_PROOF'], subject.CONFIG['MERGED_SOURCE'])
        self.assertEqual(subject.CONFIG['SOURCE_TREE'], '97bebf63ab89a3718ec172614ad5d3561e18d1d0')

    def test_publication_configuration_keeps_all_admissions_pending(self):
        self.assertEqual(subject.CONFIG['BASE_RECORDINGS'], 128)
        self.assertEqual(subject.CONFIG['PUBLIC_RECORDINGS'], 132)
        self.assertEqual(subject.CONFIG['EXPECTED_TEST_COUNT'], 116)
        self.assertEqual(subject.CONFIG['EXPECTED_FAMILY_COUNTS'], {'synth90s': 4})
        self.assertEqual(subject.CONFIG['ARTIFACT_NAME'], 'synth-third-directions-audition-candidates')
        self.assertEqual(subject.CONFIG['WORKFLOW_PATH'], '.github/workflows/synth-third-directions-intake.yml')
        self.assertEqual(subject.CONFIG['BINDING_FORMAT'], 'revealline-synth-third-directions-intake-binding.v1')

    def test_permanent_merge_commit_proves_the_original_runner_tree(self):
        saved = {name: getattr(assembler, name) for name in subject.CONFIG}
        try:
            subject.configure()
            metadata = {
                'id': assembler.ARTIFACT,
                'size_in_bytes': assembler.ZIP_BYTES,
                'digest': 'sha256:' + assembler.ZIP_SHA,
                'expired': False,
                'name': assembler.ARTIFACT_NAME,
                'workflow_run': {'head_sha': assembler.SOURCE_HEAD, 'id': assembler.RUN},
            }
            run = {
                'id': assembler.RUN,
                'head_sha': assembler.SOURCE_HEAD,
                'conclusion': 'success',
                'event': 'pull_request',
                'path': assembler.WORKFLOW_PATH,
            }
            source = {'sha': assembler.SOURCE_HEAD, 'tree': {'sha': assembler.SOURCE_TREE}}
            tree_proof = {
                'sha': assembler.TREE_PROOF,
                'tree': {'sha': assembler.SOURCE_TREE},
                'parents': [{'sha': assembler.SOURCE_BASE}, {'sha': assembler.SOURCE_HEAD}],
            }
            assembler.validate_remote(metadata, run, source, tree_proof)
            changed = copy.deepcopy(tree_proof)
            changed['tree']['sha'] = 'f' * 40
            with self.assertRaisesRegex(ValueError, 'runner tree binding'):
                assembler.validate_remote(metadata, run, source, changed)
        finally:
            for name, value in saved.items():
                setattr(assembler, name, value)

    def test_single_batch_page_preserves_mixed_license_and_content_id_status(self):
        tracks = [
            {
                'title': 'Neon', 'artist': 'Artist', 'artistURL': 'https://example.com/artist',
                'durationSeconds': 180, 'family': 'synth90s', 'credit': 'Credit',
                'changes': 'Converted.', 'vocalContent': 'unverified', 'contentId': False,
                'originalFilename': 'native.flac', 'sha256': 'a' * 64,
                'path': 'objects/' + 'a' * 64 + '.mp3', 'source': 'https://example.com/source',
                'licenseURL': 'https://creativecommons.org/licenses/by/3.0/',
                'license': 'CC BY 3.0 Unported',
            }
        ]
        page = assembler.page('One audition', tracks, 'related-batch')
        self.assertIn(b'1 complete licensed recording', page)
        self.assertIn(b'CC BY 3.0 Unported', page)
        self.assertIn(b'Content ID disabled', page)
        self.assertNotIn(b'>CC BY 4.0<', page)

    def test_main_applies_configuration_before_guarded_assembly(self):
        saved = {name: getattr(assembler, name) for name in subject.CONFIG}
        saved.update({
            'MANIFEST_SHA256': assembler.MANIFEST_SHA256,
            'checked_manifest': assembler.checked_manifest,
            'UPLOAD_PINS': assembler.UPLOAD_PINS,
            'DESCRIPTION_HASHES': assembler.DESCRIPTION_HASHES,
        })
        try:
            with patch.object(assembler, 'main') as run:
                subject.main()
                run.assert_called_once_with()
                for name, value in subject.CONFIG.items():
                    self.assertEqual(getattr(assembler, name), value)
        finally:
            for name, value in saved.items():
                setattr(assembler, name, value)


if __name__ == '__main__':
    unittest.main()
