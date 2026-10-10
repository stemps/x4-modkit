"""Translation gate shared by every mod: one English source, full locale coverage, safe formatting.

Conventions (the same for every mod, no switches):
- English lives in src/t/0001.xml, root <language> without an id. The engine uses it
  when 0001-l044.xml is absent; shipping both would keep two English copies.
- Every other game locale has 0001-lNNN.xml with <language id="NNN"> and exactly the
  English page/text ids.
- Formatting must survive translation: Lua specifiers in order, numbered MD arguments,
  {page,t} references and literal \\n counts. translations.json at the repository root
  can exempt an entry from this one rule, with a reason; an exemption that is no
  longer needed is an error, so the list cannot rot.

Checks structure and formatting, not linguistic quality. Standard library only.
"""
from collections import Counter
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

SOURCE = '0001.xml'
ENGLISH = '0001-l044.xml'
# Every locale in the game reference except English (44), including Bulgarian (359),
# Turkish (90) and Ukrainian (380), which the language selector may not enable.
LANGUAGES = {7, 33, 34, 39, 42, 48, 49, 55, 81, 82, 86, 88, 90, 359, 380}
EXEMPTIONS = 'translations.json'
# Lua arguments are positional by order; MD arguments are explicitly numbered.
TOKENS = re.compile(r'(?P<lua>%(?:%|[-+#0]*\d*(?:\.\d+)?[cdiouxXeEfgGqs]))|(?P<md>%[1-9]\d*)')
REFERENCES = re.compile(r'\{\d+,\d+\}')


def format_signature(text):
    matches = list(TOKENS.finditer(text))
    return (
        [match.group() for match in matches if match.lastgroup == 'lua'],
        Counter(match.group() for match in matches if match.lastgroup == 'md'),
        Counter(REFERENCES.findall(text)),
        text.count(r'\n'),
    )


def load_exemptions(root):
    """{(page, text): reason} from translations.json; a missing file means none."""
    path = Path(root) / EXEMPTIONS
    if not path.is_file():
        return {}, []
    errors = []
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        return {}, [f'{EXEMPTIONS}: {exc}']
    if not isinstance(data, dict) or set(data) - {'format_exemptions'}:
        return {}, [f'{EXEMPTIONS}: expected only a "format_exemptions" object']
    exemptions = {}
    for key, reason in (data.get('format_exemptions') or {}).items():
        match = re.fullmatch(r'(\d+)/(\d+)', key)
        if not match or not isinstance(reason, str) or not reason.strip():
            errors.append(f'{EXEMPTIONS}: "{key}" needs the form "page/text" and a non-empty reason')
            continue
        exemptions[(match[1], match[2])] = reason
    return exemptions, errors


def translation_errors(directory, languages=LANGUAGES, exemptions=None):
    """Every problem across all pages and locales, so one run lists everything to fix.

    Equal English text is allowed: shared terms, units and format-only entries are
    legitimate translations.
    """
    directory = Path(directory)
    exemptions = exemptions or {}
    errors = []

    def read(path, language):
        values = {}
        try:
            root = ET.parse(path).getroot()
        except (OSError, ET.ParseError) as exc:
            errors.append(f'{path.name}: {exc}')
            return values
        if root.tag != 'language':
            errors.append(f'{path.name}: expected a language document')
        if language is None and root.get('id') is not None:
            errors.append(f'{path.name}: the English source takes no language id')
        if language is not None and root.get('id') != str(language):
            errors.append(f'{path.name}: language id must be {language}')
        for page in root.findall('page'):
            for entry in page.findall('t'):
                key = (page.get('id'), entry.get('id'))
                label = f'{path.name}: page {key[0]}, text {key[1]}'
                if None in key:
                    errors.append(f'{label}: missing id attribute')
                if key in values:
                    errors.append(f'{label}: duplicate entry')
                values[key] = ''.join(entry.itertext())
                if not values[key].strip():
                    errors.append(f'{label}: empty translation')
                if re.search(r'(?<!\\)[()]', values[key]):
                    errors.append(f'{label}: unescaped parentheses; X4 would strip visible text')
                if '—' in values[key]:
                    errors.append(f'{label}: unsupported em dash; use a normal hyphen')
        if not values:
            errors.append(f'{path.name}: no text entries')
        return values

    if (directory / ENGLISH).exists():
        errors.append(f'{ENGLISH}: English belongs only in {SOURCE}; remove this second copy')
    source = read(directory / SOURCE, None) if (directory / SOURCE).exists() else {}
    if not (directory / SOURCE).exists():
        errors.append(f'{SOURCE}: missing English source')
    expected = {f'0001-l{language:03d}.xml' for language in languages}
    actual = {path.name for path in directory.glob('0001-l*.xml')} - {ENGLISH}
    for name in sorted(expected - actual):
        errors.append(f'{name}: missing language file')
    used = set()
    for name in sorted(actual):
        match = re.fullmatch(r'0001-l(\d{3})\.xml', name)
        if not match:
            errors.append(f'{name}: invalid language filename')
            continue
        values = read(directory / name, int(match[1]))
        for page, entry in sorted(source.keys() - values.keys(), key=str):
            errors.append(f'{name}: page {page}, text {entry}: missing translation')
        for page, entry in sorted(values.keys() - source.keys(), key=str):
            errors.append(f'{name}: page {page}, text {entry}: absent from English source')
        for key in sorted(source.keys() & values.keys(), key=str):
            if format_signature(values[key]) != format_signature(source[key]):
                if key in exemptions:
                    used.add(key)
                else:
                    errors.append(f'{name}: page {key[0]}, text {key[1]}: '
                                  'formatting placeholders, references or line breaks differ')
    for page, entry in sorted(exemptions.keys() - used, key=str):
        errors.append(f'{EXEMPTIONS}: {page}/{entry} is exempt but no translation needs it; remove it')
    return errors


def check(root):
    """(errors, summary) for a mod repository's src/t."""
    exemptions, errors = load_exemptions(root)
    directory = Path(root) / 'src' / 't'
    errors += translation_errors(directory, exemptions=exemptions)
    if errors:
        return errors, None
    count = len(ET.parse(directory / SOURCE).findall('page/t'))
    exempt = f', {len(exemptions)} documented format exemption(s)' if exemptions else ''
    return [], (f'{count} entries in English and each of {len(LANGUAGES)} translations; '
                f'formatting preserved{exempt}')
