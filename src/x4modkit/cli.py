"""x4mod: shared release, publication and game-link tasks for X4 mod repositories.

Run from anywhere inside a mod repository (the nearest folder with src/content.xml),
or name it with --root.
"""
import argparse
import os
from pathlib import Path
import subprocess
import sys

from . import doctor, gamelink, gamelog, release, scaffold, settings, translations
from .release_archive import ReleaseError, find_root

RELEASE_HELP = {
    'release': 'validate, record, push, package and publish a release from clean main',
    'build-zip': 'package src/ from the working tree, including uncommitted files',
    'build-workshop': 'stage src/ as a Workshop folder in dist/workshop/local',
    'workshop-placeholder': 'minimal folder for the one-time Workshop item creation',
    'publish-nexus': 'publish or resume a tagged release on Nexus Mods',
    'publish-steam': 'publish or resume a tagged release on the Steam Workshop',
    'publish-discord': 'announce a published release in the discord.json channel',
}
RELEASE_COMMANDS = tuple(RELEASE_HELP)
TEST_MODULES = ('test_release', 'test_manual_bbcode', 'test_nexus', 'test_archive',
                'test_release_support', 'test_workshop', 'test_discord', 'test_translations', 'test_scaffold', 'test_kit')


def run_tests(root, verbose=False):
    """Each module in its own process, as the per-mod scripts did, against this mod's files."""
    env = dict(os.environ)
    if root:
        env['X4MODKIT_MOD_ROOT'] = str(root)
    else:
        env.pop('X4MODKIT_MOD_ROOT', None)
    failed = []
    for module in TEST_MODULES:
        command = [sys.executable, '-m', 'unittest', *(['-v'] if verbose else []), f'x4modkit.tests.{module}']
        print(f'== {module}', flush=True)
        if subprocess.run(command, env=env).returncode:
            failed.append(module)
    target = root or 'the bundled sample mod'
    if failed:
        print(f'FAILED against {target}: {", ".join(failed)} ({len(failed)} of {len(TEST_MODULES)} modules)',
              file=sys.stderr)
        return 1
    print(f'All {len(TEST_MODULES)} test modules passed against {target}.')
    return 0


def parser():
    cli = argparse.ArgumentParser(prog='x4mod', description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    cli.add_argument('--root', type=Path, help='mod repository root (default: found from the working directory)')
    sub = cli.add_subparsers(dest='command', required=True, metavar='command')
    for name in RELEASE_COMMANDS:
        # Options are parsed by release.main; `x4mod <command> --help` lists them.
        sub.add_parser(name, add_help=False, help=RELEASE_HELP[name])
    description = sub.add_parser('description', help='render the manual at a ref as BBCode and open it')
    description.add_argument('ref', help='release tag (vMAJOR.MINOR.PATCH), branch or other commit-ish')
    description.add_argument('--target', choices=('nexus', 'steam'), default='nexus')
    for name, text in (('link', 'junction src/ into the game extensions folder'),
                       ('unlink', 'remove that junction; never deletes a regular folder'),
                       ('link-status', 'show what the extensions folder holds for this mod')):
        link = sub.add_parser(name, help=text)
        link.add_argument('--source', default='src', help='repo-relative mod folder (default: src)')
        link.add_argument('--name', help='extensions folder name (default: the repository folder name)')
    sub.add_parser('translations', help='check src/t against the English source 0001.xml')
    sub.add_parser('log', help="follow the game's debug log")
    test = sub.add_parser('test', help="release tooling tests, with live checks of this mod's files")
    test.add_argument('--sample', action='store_true', help='test against the bundled sample mod instead')
    test.add_argument('-v', '--verbose', action='store_true')
    sub.add_parser('doctor', help='report drift: stale copies of kit files, edited shared justfile block')
    sub.add_parser('justfile', help='print the shared justfile block to paste into a mod')
    sub.add_parser('config', help='show the resolved machine-local paths and where each came from')
    new = sub.add_parser('new', help='create a new mod repository that already passes the kit checks')
    new.add_argument('id', help='content.xml id and folder name: lowercase letters, digits, underscores')
    new.add_argument('name', help='display name, e.g. "Better Trading"')
    new.add_argument('--description', help='one-line description for content.xml, Nexus and the manual')
    new.add_argument('--author', help='default: git config user.name')
    new.add_argument('--page', type=int, help='text page id (default: derived from the id, 900000-999999)')
    new.add_argument('--save', action='store_true',
                     help='content.xml save="true": needed when the mod adds content saves depend on')
    new.add_argument('--dir', type=Path, default=Path('.'), help='parent folder (default: current folder)')
    return cli


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    cli = parser()
    # Release commands keep their own argument parser; hand over everything after the name.
    args, rest = cli.parse_known_args(argv)
    if rest and args.command not in RELEASE_COMMANDS:
        cli.error('unrecognized arguments: ' + ' '.join(rest))
    try:
        if args.command == 'justfile':
            print(doctor.shared_block(), end='')
            return 0
        if args.command == 'config':
            print(f'config file: {settings.config_path()}'
                  + ('' if settings.config_path().is_file() else ' (missing)'))
            for key, text in settings.KEYS.items():
                print(f'{key:16} {settings.get(key) or "-"}  [{settings.source(key) or "unset"}] {text}')
            return 0
        if args.command == 'new':
            target, page = scaffold.create(args.dir / args.id, args.id, args.name, args.description,
                                           args.author, args.page, args.save)
            save = 'true' if args.save else 'false'
            print(f'Created {target.resolve()} (text page {page}, save="{save}").')
            print('Next: add your files under src/, extend the `check` recipe, `just link` to test in game.')
            print('Before the first `just release`: push main to a remote and put the Nexus mod id '
                  'into nexus.json.')
            return 0
        if args.command == 'test' and args.sample:
            return run_tests(None, args.verbose)
        root = args.root.resolve() if args.root else find_root()
        if args.command in RELEASE_COMMANDS:
            release.main([args.command, *rest], root=root)
        elif args.command == 'description':
            from .manual_bbcode import resolve, handoff
            commit, label = resolve(root, args.ref)
            handoff(root, label, commit, args.target)
        elif args.command in ('link', 'unlink', 'link-status'):
            action = 'status' if args.command == 'link-status' else args.command
            print(gamelink.run(root, action, source=args.source, name=args.name))
        elif args.command == 'translations':
            errors, summary = translations.check(root)
            for error in errors:
                print(f'FAIL translations: {error}', file=sys.stderr)
            if errors:
                return 1
            print(f'PASS translations: {summary}')
        elif args.command == 'log':
            gamelog.follow()
        elif args.command == 'test':
            return run_tests(root, args.verbose)
        elif args.command == 'doctor':
            found = doctor.problems(root)
            for problem in found:
                print(f'drift: {problem}', file=sys.stderr)
            if found:
                return 1
            print(f'No drift: {root} uses x4-modkit and its shared justfile block is current.')
        return 0
    except KeyboardInterrupt:
        return 130
    except (ReleaseError, subprocess.CalledProcessError, OSError, ValueError, EOFError) as error:
        label = 'Release' if args.command in RELEASE_COMMANDS else args.command.capitalize()
        print(f'{label} aborted: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
