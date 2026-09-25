import ast
from pathlib import Path
import unittest

import itch_audio
import prepare_approved_directions
import prepare_purgatory3
import prepare_reckless2
import prepare_second_directions
import prepare_synth_third_directions


ROOT = Path(__file__).parent.parent
ENTRY_POINTS = (
    prepare_approved_directions,
    prepare_second_directions,
    prepare_purgatory3,
    prepare_reckless2,
    prepare_synth_third_directions,
)


def imported_pin_files(path):
    tree = ast.parse((ROOT / path).read_text())
    return {
        'intake/' + node.module + '.py'
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and isinstance(node.module, str)
        and node.module.endswith('_pins')
    }


class BindingSourceTests(unittest.TestCase):
    def test_shared_pin_list_matches_every_resolver_import(self):
        expected = set(itch_audio.PIN_FILES)
        self.assertEqual(imported_pin_files('intake/itch_source.py'), expected)
        self.assertEqual(imported_pin_files('intake/itch_audio.py'), expected)

    def test_every_hosted_entry_binds_all_shared_acquisition_sources(self):
        expected = set(itch_audio.SHARED_ACQUISITION_FILES)
        for entry in ENTRY_POINTS:
            with self.subTest(entry=entry.__name__):
                files = entry.SOURCE_FILES
                self.assertEqual(len(files), len(set(files)))
                self.assertTrue(expected.issubset(files))
                self.assertIn(entry.WORKFLOW, files)
                self.assertIn('intake/' + entry.__name__ + '.py', files)
                workflow = (ROOT / entry.WORKFLOW).read_text()
                self.assertTrue(
                    "- 'intake/itch_audio.py'" in workflow
                    or entry is prepare_synth_third_directions
                )


if __name__ == '__main__':
    unittest.main()
