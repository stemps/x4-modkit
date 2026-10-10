"""Detect drift between a mod repository and the kit: stale copies and an edited shared block."""
from importlib import resources
from pathlib import Path

# Files the kit owns. A copy left in a mod is dead code that drifts unnoticed.
KIT_OWNED = (
    'scripts/release.py', 'scripts/release_archive.py', 'scripts/manual_bbcode.py',
    'scripts/nexus_publish.py', 'scripts/steam_publish.py', 'scripts/discord_publish.py',
    'scripts/workshop_build.py', 'scripts/game_link.ps1', 'scripts/game_log.ps1',
    'tests/release',
)


def shared_block():
    return resources.files('x4modkit').joinpath('shared.just').read_text(encoding='utf-8')


def _lines(text):
    return [line.rstrip() for line in text.replace('\r\n', '\n').split('\n')]


def problems(root):
    root = Path(root)
    found = [f'{name} is owned by x4-modkit; delete the local copy.'
             for name in KIT_OWNED if (root / name).exists()]
    justfile = root / 'justfile'
    if not justfile.is_file():
        found.append('justfile is missing.')
        return found
    block, have = _lines(shared_block()), _lines(justfile.read_text(encoding='utf-8'))
    while block and not block[-1]:
        block.pop()
    starts = [i for i in range(len(have)) if have[i:i + len(block)] == block]
    if not starts:
        found.append('justfile does not contain the current shared block verbatim. '
                     'Replace it with the output of `x4mod justfile`.')
    return found
