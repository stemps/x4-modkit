"""Kit plumbing: machine-local settings, root discovery, game links and drift detection."""
import contextlib
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from x4modkit import cli, doctor, gamelink, settings
from x4modkit.release_archive import ReleaseError, find_root


class Temp(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.config = self.base / 'paths.env'
        cleared = {key: '' for key in settings.KEYS}
        self.env = patch.dict(os.environ, {**cleared, 'X4MODKIT_CONFIG': str(self.config)})
        self.env.start()
        self.addCleanup(self.env.stop)

    def mod(self, name='my_mod'):
        root = self.base / name
        (root / 'src').mkdir(parents=True)
        (root / 'src' / 'content.xml').write_text('<content id="my_mod" name="My Mod"/>\n', encoding='utf-8')
        return root


class SettingsTests(Temp):
    def test_environment_beats_file_and_empty_counts_as_unset(self):
        self.config.write_text('X4_GAME="C:\\Games\\X4 Foundations"\nXRCATTOOL=\n', encoding='utf-8')
        self.assertEqual(settings.get('X4_GAME'), 'C:\\Games\\X4 Foundations')
        self.assertEqual(settings.source('X4_GAME'), 'file')
        self.assertIsNone(settings.get('XRCATTOOL'))
        with patch.dict(os.environ, {'X4_GAME': 'D:\\X4'}):
            self.assertEqual((settings.get('X4_GAME'), settings.source('X4_GAME')), ('D:\\X4', 'env'))

    def test_extensions_fall_back_to_game_folder(self):
        self.config.write_text('X4_GAME=/games/x4\n', encoding='utf-8')
        self.assertEqual(settings.extensions_dir(), Path('/games/x4/extensions'))
        self.config.write_text('X4_GAME=/games/x4\nX4_EXTENSIONS=/elsewhere\n', encoding='utf-8')
        self.assertEqual(settings.extensions_dir(), Path('/elsewhere'))

    def test_missing_configuration_names_the_config_file(self):
        with self.assertRaisesRegex(LookupError, 'paths.env'):
            settings.extensions_dir()

    def test_debug_log_from_profile(self):
        self.config.write_text('X4_PROFILE=/profile\n', encoding='utf-8')
        self.assertEqual(settings.debug_log(), Path('/profile/debug.txt'))


class RootTests(Temp):
    def test_found_from_any_subfolder_and_refused_outside(self):
        root = self.mod()
        (root / 'src' / 'md').mkdir()
        self.assertEqual(find_root(root / 'src' / 'md'), root.resolve())
        self.assertEqual(find_root(root), root.resolve())
        with self.assertRaisesRegex(ReleaseError, 'Not inside a mod repository'):
            find_root(self.base)


class LinkTests(Temp):
    def setUp(self):
        super().setUp()
        self.root = self.mod()
        (self.root / 'src' / 'keep.txt').write_text('dev file', encoding='utf-8')
        self.extensions = self.base / 'extensions'
        self.extensions.mkdir()
        self.config.write_text(f'X4_EXTENSIONS={self.extensions}\n', encoding='utf-8')

    def test_link_status_unlink_round_trip_keeps_the_dev_files(self):
        self.assertIn('Not linked', gamelink.run(self.root, 'status'))
        self.assertIn('Linked:', gamelink.run(self.root, 'link'))
        self.assertEqual((self.extensions / 'my_mod' / 'keep.txt').read_text(encoding='utf-8'), 'dev file')
        self.assertIn('Already linked', gamelink.run(self.root, 'link'))
        self.assertIn('Linked:', gamelink.run(self.root, 'status'))
        self.assertIn('Unlinked', gamelink.run(self.root, 'unlink'))
        self.assertFalse(os.path.lexists(self.extensions / 'my_mod'))
        self.assertEqual((self.root / 'src' / 'keep.txt').read_text(encoding='utf-8'), 'dev file')
        self.assertIn('Nothing to unlink', gamelink.run(self.root, 'unlink'))

    def test_regular_folder_is_never_replaced_or_deleted(self):
        (self.extensions / 'my_mod').mkdir()
        (self.extensions / 'my_mod' / 'copied.txt').write_text('deployed', encoding='utf-8')
        self.assertIn('regular folder', gamelink.run(self.root, 'status'))
        for action in ('link', 'unlink'):
            with self.subTest(action=action), self.assertRaisesRegex(ReleaseError, 'regular folder'):
                gamelink.run(self.root, action)
        self.assertTrue((self.extensions / 'my_mod' / 'copied.txt').exists())

    def test_link_to_another_folder_is_reported_and_kept(self):
        other = self.base / 'other'
        other.mkdir()
        gamelink._create(self.extensions / 'my_mod', other)
        self.assertIn('Outdated link', gamelink.run(self.root, 'status'))
        with self.assertRaisesRegex(ReleaseError, 'already links'):
            gamelink.run(self.root, 'link')

    def test_named_source_folder(self):
        (self.root / 'samples' / 'client').mkdir(parents=True)
        gamelink.run(self.root, 'link', source='samples/client', name='sample_client')
        self.assertTrue(gamelink._is_link(self.extensions / 'sample_client'))
        gamelink.run(self.root, 'unlink', source='samples/client', name='sample_client')


class DoctorTests(Temp):
    def setUp(self):
        super().setUp()
        self.root = self.mod()

    def write_justfile(self, block):
        # Bytes, so the test controls the line endings on every platform.
        (self.root / 'justfile').write_bytes(('check:\n    echo mod checks\n\n' + block).encode('utf-8'))

    def test_current_block_passes_with_lf_and_crlf(self):
        for ending in ('\n', '\r\n'):
            with self.subTest(ending=repr(ending)):
                self.write_justfile(doctor.shared_block().replace('\n', ending))
                self.assertEqual(doctor.problems(self.root), [])

    def test_edited_block_and_stale_copies_are_reported(self):
        self.write_justfile(doctor.shared_block().replace('{{x4mod}} release\n', 'python scripts/release.py\n'))
        (self.root / 'scripts').mkdir()
        (self.root / 'scripts' / 'release.py').write_text('', encoding='utf-8')
        found = doctor.problems(self.root)
        self.assertEqual(len(found), 2, found)
        self.assertIn('scripts/release.py', found[0])
        self.assertIn('shared block', found[1])

    def test_shared_block_names_every_release_command(self):
        block = doctor.shared_block()
        for command in cli.RELEASE_COMMANDS:
            with self.subTest(command=command):
                self.assertIn('{{x4mod}} ' + command, block)


class CliTests(Temp):
    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_release_commands_receive_their_arguments_and_the_found_root(self):
        root = self.mod()
        with patch.object(cli.release, 'main') as release_main, patch.object(cli, 'find_root', return_value=root):
            self.assertEqual(self.run_cli('publish-nexus', 'v1.2.3', '--adopt-version', '7')[0], 0)
        release_main.assert_called_once_with(['publish-nexus', 'v1.2.3', '--adopt-version', '7'], root=root)

    def test_outside_a_mod_fails_cleanly(self):
        with patch.object(cli, 'find_root', side_effect=ReleaseError('Not inside a mod repository')):
            code, _, err = self.run_cli('build-zip')
        self.assertEqual(code, 1)
        self.assertIn('Release aborted: Not inside a mod repository', err)

    def test_unknown_arguments_rejected_for_kit_commands(self):
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            cli.main(['doctor', '--bogus'])

    def test_test_list_covers_every_test_module(self):
        modules = {p.stem for p in Path(__file__).parent.glob('test_*.py')}
        self.assertEqual(modules, set(cli.TEST_MODULES))


if __name__ == '__main__':
    unittest.main()
