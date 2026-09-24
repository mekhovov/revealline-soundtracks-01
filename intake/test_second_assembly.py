import unittest
from unittest.mock import patch

import assemble_approved_directions as assembler
import assemble_second_directions as subject


class SecondAssemblyConfigurationTests(unittest.TestCase):
    def test_exact_artifact_and_source_binding(self):
        self.assertEqual(subject.CONFIG['RUN'], 36072262687)
        self.assertEqual(subject.CONFIG['ARTIFACT'], 10838153770)
        self.assertEqual(subject.CONFIG['ZIP_BYTES'], 140918961)
        self.assertEqual(
            subject.CONFIG['ZIP_SHA'],
            '8f2dccf2de56f3ade27038def3e5395777cd3cee37c6580ce68439ac2eb7cc25',
        )
        self.assertEqual(subject.CONFIG['SOURCE_HEAD'], '39b09d5269f0fa9a32786fdb705eb8e69a5cf33f')
        self.assertEqual(subject.CONFIG['RUNNER'], 'b3b435fa6ac788494d80b9af81d862fbb1ddd0f1')
        self.assertEqual(subject.CONFIG['SOURCE_TREE'], 'fae86c78144ca2bd1f959deee312b045be5672fb')
        self.assertEqual(subject.CONFIG['MERGED_SOURCE'], '6a1a3c42761b25c3f87121a70a6b17959088e9f4')

    def test_publication_configuration_keeps_all_approvals_false(self):
        self.assertEqual(subject.CONFIG['BASE_RECORDINGS'], 116)
        self.assertEqual(subject.CONFIG['PUBLIC_RECORDINGS'], 128)
        self.assertEqual(subject.CONFIG['EXPECTED_TEST_COUNT'], 104)
        self.assertEqual(subject.CONFIG['ARTIFACT_NAME'], 'second-directions-audition-candidates')
        self.assertEqual(subject.CONFIG['WORKFLOW_PATH'], '.github/workflows/second-directions-intake.yml')
        self.assertEqual(subject.CONFIG['BINDING_FORMAT'], 'revealline-second-directions-intake-binding.v1')
        self.assertEqual(set(subject.CONFIG['BATCH_IDS']), {'synth90s', 'metal'})

    def test_main_applies_configuration_before_calling_guarded_assembler(self):
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
