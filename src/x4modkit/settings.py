"""Machine-local paths: environment variable first, then the x4-modkit config file.

The config file holds KEY=value lines (optionally quoted), the same format as the old
toolkit x4-paths.env, so existing lines can be copied over unchanged. It lives at
$X4MODKIT_CONFIG, or ~/.config/x4-modkit/paths.env. An empty value counts as unset.
"""
import os
from pathlib import Path
import re

KEYS = {
    'X4_GAME': 'X4 game folder (holds 01.cat and extensions/)',
    'X4_EXTENSIONS': 'game-root extensions folder; defaults to $X4_GAME/extensions',
    'X4_PROFILE': 'user profile folder Documents/Egosoft/X4/<id>',
    'X4_DEBUGLOG': 'debug log; defaults to $X4_PROFILE/debug.txt, then the newest debug.txt',
    'XRCATTOOL': 'XRCatTool.exe, used to pack the Workshop catalog',
    'X4_WORKSHOPTOOL': 'WorkshopTool.exe, used to publish to the Steam Workshop',
}


def config_path():
    explicit = os.environ.get('X4MODKIT_CONFIG')
    return Path(explicit) if explicit else Path.home() / '.config' / 'x4-modkit' / 'paths.env'


def from_file(key):
    path = config_path()
    if not path.is_file():
        return None
    for line in path.read_text(encoding='utf-8').splitlines():
        match = re.fullmatch(r'\s*' + re.escape(key) + r'\s*=\s*"?([^"]*)"?\s*', line)
        if match and match[1]:
            return match[1]
    return None


def get(key):
    return os.environ.get(key) or from_file(key)


def source(key):
    """Where get(key) came from, for `x4mod config`."""
    if os.environ.get(key):
        return 'env'
    return 'file' if from_file(key) else None


def extensions_dir():
    found = get('X4_EXTENSIONS')
    if found:
        return Path(found)
    game = get('X4_GAME')
    if game:
        return Path(game) / 'extensions'
    raise LookupError('Cannot locate the game extensions folder. Set X4_EXTENSIONS or X4_GAME '
                      f'(environment variable or {config_path()}).')


def debug_log():
    found = get('X4_DEBUGLOG')
    if found:
        return Path(found)
    profile = get('X4_PROFILE')
    if profile:
        return Path(profile) / 'debug.txt'
    # Documents may be redirected into OneDrive on Windows.
    documents = (Path.home() / 'Documents', Path.home() / 'OneDrive' / 'Documents')
    logs = sorted((log for d in documents for log in (d / 'Egosoft' / 'X4').glob('*/debug.txt')),
                  key=lambda p: p.stat().st_mtime, reverse=True)
    if logs:
        return logs[0]
    raise LookupError(f'Cannot locate debug.txt. Set X4_DEBUGLOG (environment variable or {config_path()}).')
