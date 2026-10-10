"""`x4mod new`: the generated repository passes every rule the kit enforces."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from xml.etree import ElementTree as ET

from x4modkit import doctor, scaffold, translations
from x4modkit.release_archive import ReleaseError, identity, working_files

# The live checks of a real mod, run here against a fresh scaffold.
LIVE_MODULES = ('test_archive', 'test_manual_bbcode', 'test_nexus', 'test_workshop', 'test_discord')


class ScaffoldTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)

    def create(self, mod_id='better_trading', name='Better Trading (Beta)', **kwargs):
        kwargs.setdefault('author', 'Test Author')
        return scaffold.create(self.base / mod_id, mod_id, name, **kwargs)

    def test_generated_mod_passes_doctor_and_translations(self):
        root, page = self.create(description='Trade "better" & faster <now>.')
        self.assertEqual(doctor.problems(root), [])
        errors, summary = translations.check(root)
        self.assertEqual(errors, [])
        self.assertIn('1 entries in English and each of 15 translations', summary)
        self.assertEqual(page, scaffold.default_page('better_trading'))
        manifest = (root / 'src' / 'content.xml').read_bytes()
        self.assertEqual(identity(manifest), ('better_trading', 'Better-Trading-Beta'))
        content = ET.fromstring(manifest)
        self.assertEqual((content.get('description'), content.get('save'), content.get('version')),
                         ('Trade "better" & faster <now>.', 'false', '0'))
        self.assertEqual((root / 'src' / 'MIT-LICENSE').read_bytes(), (root / 'MIT-LICENSE').read_bytes())
        self.assertIn('Test Author', (root / 'MIT-LICENSE').read_text(encoding='utf-8'))
        self.assertTrue((root / '.gitignore').is_file())
        self.assertFalse((root / 'src' / 'ui.xml').exists())
        self.assertFalse((root / 'VERSION').exists())

    def test_no_placeholder_survives_and_no_em_dash_is_written(self):
        root, _ = self.create()
        for path in root.rglob('*'):
            if path.is_file() and '.git' not in path.parts:
                text = path.read_text(encoding='utf-8')
                with self.subTest(path=path.relative_to(root)):
                    self.assertIsNone(re.search(r'@[A-Z_]+@', text))
                    self.assertNotIn('—', text)

    def test_parentheses_in_the_name_are_escaped_in_text_files(self):
        root, _ = self.create()
        source = ET.parse(root / 'src' / 't' / '0001.xml').find('page/t').text
        self.assertEqual(source, 'Better Trading \\(Beta\\)')

    def test_runtime_files_package_without_ui_manifest(self):
        root, _ = self.create()
        subprocess.run(['git', 'add', '--', 'src'], cwd=root, check=True, capture_output=True)
        files = working_files(root)
        self.assertIn('content.xml', files)
        self.assertEqual(sum(name.startswith('t/') for name in files), 16)

    def test_save_flag_page_and_git(self):
        root, page = self.create('save_mod', 'Save Mod', page=912345, save=True)
        self.assertEqual(page, 912345)
        self.assertEqual(ET.parse(root / 'src' / 'content.xml').getroot().get('save'), 'true')
        self.assertEqual(ET.parse(root / 'src' / 't' / '0001-l049.xml').find('page').get('id'), '912345')
        if shutil.which('git'):
            branch = subprocess.run(['git', 'symbolic-ref', '--short', 'HEAD'], cwd=root,
                                    capture_output=True, text=True).stdout.strip()
            self.assertEqual(branch, 'main')

    def test_refusals_write_nothing(self):
        (self.base / 'taken').mkdir()
        for mod_id, name, pattern in (('taken', 'Taken', 'already exists'),
                                      ('Bad-Id', 'Bad', 'mod id'),
                                      ('ok_id', 'Ümlaut', 'name must be'),
                                      ('ok_id', 'A—B', 'name must be')):
            with self.subTest(mod_id=mod_id, name=name), self.assertRaisesRegex(ReleaseError, pattern):
                scaffold.create(self.base / mod_id, mod_id, name, author='Test Author')
        self.assertEqual(sorted(p.name for p in self.base.iterdir()), ['taken'])
        self.assertEqual(list((self.base / 'taken').iterdir()), [])

    @unittest.skipIf(os.environ.get('X4MODKIT_MOD_ROOT'), 'the scaffold is checked by the kit, not by each mod')
    def test_live_checks_pass_against_a_fresh_scaffold(self):
        root, _ = self.create()
        env = {**os.environ, 'X4MODKIT_MOD_ROOT': str(root)}
        result = subprocess.run([sys.executable, '-m', 'unittest', *(f'x4modkit.tests.{m}' for m in LIVE_MODULES)],
                                env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr[-3000:])

    @unittest.skipUnless(shutil.which('just'), 'just is not installed')
    def test_justfile_parses_and_wires_the_release_gate(self):
        root, _ = self.create()
        result = subprocess.run(['just', '--dry-run', 'check-release'], cwd=root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        for command in ('x4mod translations', 'x4mod doctor', 'x4mod test'):
            self.assertIn(command, result.stderr + result.stdout)


if __name__ == '__main__':
    unittest.main()
