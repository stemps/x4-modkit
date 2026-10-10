"""Link a mod folder into the game's extensions folder for in-game testing.

Windows uses a directory junction (no admin rights needed), elsewhere a symlink. Never
deletes a regular folder and never touches the link target's contents.
"""
import os
from pathlib import Path

from . import settings
from .release_archive import ReleaseError, MOD


def _is_link(path):
    return path.is_symlink() or (hasattr(os.path, 'isjunction') and os.path.isjunction(path))


def _target(path):
    target = os.readlink(path)
    # Junction targets come back in NT form on Windows.
    return target[4:] if target.startswith('\\\\?\\') else target


def _same(a, b):
    return os.path.normcase(os.path.realpath(a)) == os.path.normcase(os.path.realpath(b))


def _create(link, source):
    if os.name == 'nt':
        import _winapi
        _winapi.CreateJunction(str(source), str(link))
    else:
        os.symlink(source, link, target_is_directory=True)


def run(root, action, source=MOD, name=None, extensions=None):
    root = Path(root).resolve()
    source_dir = (root / source).resolve()
    if not source_dir.is_dir():
        raise ReleaseError(f'Mod folder not found: {source_dir}')
    try:
        extensions = Path(extensions) if extensions else settings.extensions_dir()
    except LookupError as error:
        raise ReleaseError(str(error)) from None
    if not extensions.is_dir():
        raise ReleaseError(f'Extensions folder not found: {extensions}')
    link = extensions / (name or root.name)
    exists = os.path.lexists(link)
    is_link = exists and _is_link(link)
    target = _target(link) if is_link else None

    if action == 'status':
        if not exists:
            return f'Not linked: {link} does not exist.'
        if is_link and not _same(target, source_dir):
            return f'Outdated link: {link} -> {target} (expected {source_dir}). Unlink it, then link again.'
        if is_link:
            return f'Linked: {link} -> {target}'
        return f'Not a link: {link} is a regular folder (copied deploy?).'
    if action == 'link':
        if is_link:
            if _same(target, source_dir):
                return f'Already linked: {link} -> {target}'
            raise ReleaseError(f'{link} already links to {target}. Unlink it first.')
        if exists:
            raise ReleaseError(f'{link} exists as a regular folder. Remove or rename it first; refusing to overwrite.')
        _create(link, source_dir)
        return f'Linked: {link} -> {source_dir}'
    if action == 'unlink':
        if not exists:
            return f'Nothing to unlink: {link} does not exist.'
        if not is_link:
            raise ReleaseError(f'{link} is a regular folder, not a link. Refusing to delete it.')
        # Removes only the junction or symlink itself, never the target's contents.
        if link.is_symlink() and os.name != 'nt':
            link.unlink()
        else:
            os.rmdir(link)
        return f'Unlinked: {link} (was -> {target})'
    raise ValueError(f'Unknown link action: {action}')
