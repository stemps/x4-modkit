"""`x4mod new`: a complete, valid mod repository that already passes doctor and translations.

Templates live in templates/ with @TOKEN@ placeholders. The justfile gets the shared
block from shared.just and the translation files are generated from LANGUAGES, so the
scaffold cannot drift from the rules the kit enforces.
"""
import datetime
from importlib import resources
import json
from pathlib import Path
import re
import shutil
import subprocess
from xml.sax.saxutils import escape
import zlib

from . import doctor, translations
from .release_archive import ReleaseError

# Nexus display_name rules (nexus_publish), which the release enforces later anyway.
NAME = re.compile(r"[a-zA-Z0-9 _'().-]{1,50}")
ID = re.compile(r'[a-z][a-z0-9_]{2,49}')
# Packaged without a leading dot: build tools can drop dotfiles from package data.
RENAMES = {'gitignore': '.gitignore'}


def default_page(mod_id):
    """A stable text page id in 900000-999999, far above vanilla's (highest 30622).

    t/ files are unioned across base, DLC and mods, so two mods sharing a page merge
    their entries. A hash of the mod id keeps collisions unlikely, not impossible.
    """
    return 900000 + zlib.crc32(mod_id.encode()) % 100000


def git_author():
    try:
        result = subprocess.run(['git', 'config', 'user.name'], capture_output=True, text=True)
    except OSError:
        return None
    return result.stdout.strip() or None


def _render(text, suffix, values):
    def value(match):
        raw = values[match[1]]
        if suffix == '.xml':
            return escape(raw, {'"': '&quot;'})
        if suffix == '.json':
            return json.dumps(raw)[1:-1]
        return raw
    rendered = re.sub(r'@([A-Z_]+)@', value, text)
    leftover = re.findall(r'@[A-Z_]+@', rendered)
    if leftover:
        raise ValueError(f'Unfilled scaffold placeholders: {leftover}')
    return rendered


def _text_file(language, page, name):
    # X4 strips unescaped parentheses as translator comments.
    label = escape(name).replace('(', '\\(').replace(')', '\\)')
    attribute = f' id="{language}"' if language is not None else ''
    return ('<?xml version="1.0" encoding="utf-8"?>\n'
            + (f'<!-- Page {page} belongs to this mod. t/ files are unioned across base, DLC and\n'
               '     mods, so another mod using the same page id would merge entries with it. -->\n'
               if language is None else '')
            + f'<language{attribute}>\n'
            + f'  <page id="{page}" title="{escape(name, {chr(34): "&quot;"})}" voice="no">\n'
            + f'    <t id="1">{label}</t>\n'
            + '  </page>\n</language>\n')


def create(target, mod_id, name, description=None, author=None, page=None, save=False, init_git=True):
    target = Path(target)
    if not ID.fullmatch(mod_id):
        raise ReleaseError('The mod id must be 3-50 characters: a lowercase letter, then lowercase '
                           'letters, digits or underscores.')
    if not NAME.fullmatch(name) or not re.search(r'[A-Za-z0-9]', name):
        raise ReleaseError("The name must be 1-50 characters from letters, digits, spaces and _'().- "
                           '(the Nexus display name rule).')
    if '—' in (description or '') + name:
        raise ReleaseError('Use a normal hyphen instead of an em dash; the game cannot render it.')
    author = author or git_author()
    if not author:
        raise ReleaseError('No author: pass --author or set git config user.name.')
    if target.exists():
        raise ReleaseError(f'{target} already exists; refusing to write into it.')
    page = page or default_page(mod_id)
    today = datetime.date.today()
    values = {'MOD_ID': mod_id, 'MOD_NAME': name, 'DESCRIPTION': description or f'{name} for X4: Foundations.',
              'AUTHOR': author, 'YEAR': str(today.year), 'DATE': today.isoformat(), 'PAGE': str(page),
              'SAVE': 'true' if save else 'false'}

    templates = resources.files('x4modkit').joinpath('templates')
    written = []

    def walk(folder, relative):
        for item in sorted(folder.iterdir(), key=lambda entry: entry.name):
            path = relative / RENAMES.get(item.name, item.name)
            if item.is_dir():
                walk(item, path)
                continue
            text = _render(item.read_text(encoding='utf-8'), Path(item.name).suffix, values)
            if path.as_posix() == 'justfile':
                text += doctor.shared_block()
            destination = target / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(text, encoding='utf-8', newline='\n')
            written.append(path.as_posix())

    try:
        walk(templates, Path())
        shutil.copyfile(target / 'MIT-LICENSE', target / 'src' / 'MIT-LICENSE')
        t = target / 'src' / 't'
        t.mkdir(parents=True)
        (t / translations.SOURCE).write_text(_text_file(None, page, name), encoding='utf-8', newline='\n')
        for language in sorted(translations.LANGUAGES):
            (t / f'0001-l{language:03d}.xml').write_text(_text_file(language, page, name),
                                                         encoding='utf-8', newline='\n')
        problems = doctor.problems(target) + translations.check(target)[0]
        if problems:
            raise ReleaseError('The scaffold failed its own checks: ' + '; '.join(problems))
    except BaseException:
        shutil.rmtree(target, ignore_errors=True)
        raise
    if init_git and shutil.which('git'):
        subprocess.run(['git', 'init', '-q', '-b', 'main'], cwd=target, check=True)
    return target, page
