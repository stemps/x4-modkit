"""Translation gate: coverage, escapes and formatting across all locales."""
from pathlib import Path
import tempfile
import unittest

import json

from x4modkit import translations
from x4modkit.translations import translation_errors


class TranslationCoverageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = '<page id="90210"><t id="1">Stations</t></page>'
        self.source += '<page id="90211"><t id="1">%s/h</t></page>'
        self.write("0001.xml", self.source)
        self.write("0001-l049.xml", self.source)
        self.exemptions = {}

    def write(self, name, body):
        language = f' id="{int(name[6:9])}"' if name != '0001.xml' else ''
        (self.root / name).write_text(f'<language{language}>{body}</language>', encoding="utf-8")

    def errors(self):
        return translation_errors(self.root, {49}, self.exemptions)

    def test_complete_multiple_pages_and_shared_words_pass(self):
        self.assertEqual(self.errors(), [])

    def test_missing_entry_on_second_page_is_reported(self):
        self.write("0001-l049.xml", '<page id="90210"><t id="1">Stationen</t></page>')
        self.assertEqual(self.errors(), [
            "0001-l049.xml: page 90211, text 1: missing translation"])

    def test_missing_language_file_fails(self):
        (self.root / "0001-l049.xml").unlink()
        self.assertIn("0001-l049.xml: missing language file", self.errors())

    def test_empty_translation_fails(self):
        self.write("0001-l049.xml", self.source.replace("Stations", " \n "))
        self.assertTrue(any("empty translation" in error for error in self.errors()))

    def test_duplicate_entry_fails(self):
        self.write("0001-l049.xml", self.source + self.source)
        self.assertEqual(sum("duplicate entry" in error for error in self.errors()), 2)

    def test_all_languages_are_reported_together(self):
        self.write("0001-l033.xml", '<page id="90210"><t id="1">Stations</t></page>')
        self.write("0001-l049.xml", '<page id="90211"><t id="1">%s/h</t></page>')
        self.assertEqual(sum("missing translation" in error for error in self.errors()), 2)

    def test_malformed_xml_is_reported(self):
        (self.root / "0001-l049.xml").write_text("<language>", encoding="utf-8")
        self.assertTrue(any("no element found" in error for error in self.errors()))

    def test_extra_entry_fails(self):
        self.write("0001-l049.xml", self.source + '<page id="99"><t id="2">Extra</t></page>')
        self.assertTrue(any("absent from English source" in error for error in self.errors()))

    def test_unescaped_parentheses_checked_on_every_page_and_language(self):
        for name in ['0001.xml', '0001-l049.xml', '0001-l033.xml']:
            self.write(name, self.source.replace('%s/h', '%s/h (examples)'))
        errors = self.errors()
        for name in ['0001.xml', '0001-l049.xml', '0001-l033.xml']:
            self.assertIn(f'{name}: page 90211, text 1: unescaped parentheses; X4 would strip visible text', errors)
        self.assertEqual(len(errors), 3)

    def test_escaped_parentheses_and_xml_comments_are_allowed(self):
        source = self.source.replace('%s/h', r'%s/h \(examples\)')
        for name in ['0001.xml', '0001-l049.xml']:
            self.write(name, source + '<!-- (translator note) -->')
        self.assertEqual(self.errors(), [])

    def test_unescaped_closing_parenthesis_is_reported(self):
        self.write('0001-l049.xml', self.source.replace('Stations', r'Stationen \(Beispiele)'))
        self.assertTrue(any('unescaped parentheses' in error for error in self.errors()))

    def test_wrong_language_id_fails(self):
        path = self.root / '0001-l049.xml'
        path.write_text(path.read_text(encoding='utf-8').replace('id="49"', 'id="44"'), encoding='utf-8')
        self.assertIn('0001-l049.xml: language id must be 49', self.errors())

    def test_missing_source_fails(self):
        (self.root / '0001.xml').unlink()
        self.assertIn('0001.xml: missing English source', self.errors())

    def test_empty_source_fails(self):
        self.write('0001.xml', '')
        self.assertIn('0001.xml: no text entries', self.errors())

    def test_wrong_root_and_missing_ids_fail(self):
        (self.root / '0001-l049.xml').write_text('<wrong id="49"><page><t>Text</t></page></wrong>', encoding='utf-8')
        self.assertTrue(any('expected a language document' in error for error in self.errors()))
        self.assertTrue(any('missing id attribute' in error for error in self.errors()))

    def assert_formats(self, english, translated, valid):
        self.write('0001.xml', f'<page id="1"><t id="1">{english}</t></page>')
        self.write('0001-l049.xml', f'<page id="1"><t id="1">{translated}</t></page>')
        errors = self.errors()
        if valid:
            self.assertEqual(errors, [])
        else:
            self.assertTrue(any('formatting placeholders' in error for error in errors), errors)

    def test_lua_placeholder_type_order_precision_and_percent_are_preserved(self):
        for translated in ['%d %.1f %s %%', '%s %.0f %d %%', '%s %.1f %d %', '%s %.1f %%']:
            with self.subTest(translated=translated):
                self.assert_formats('%s %.1f %d %%', translated, False)

    def test_numbered_md_placeholders_may_be_reordered(self):
        self.assert_formats('%1 in %2: %3%.', '%3%: %2, %1.', True)

    def test_numbered_md_placeholders_cannot_be_lost_or_duplicated(self):
        for translated in ['%1 %2', '%1 %2 %2', '%1 %2 %4']:
            with self.subTest(translated=translated):
                self.assert_formats('%1 %2 %3', translated, False)

    def test_literal_percent_text_is_not_a_lua_placeholder(self):
        self.assert_formats('90% of demand; 10% for reserves', '90% des Bedarfs; 10% Reserve', True)

    def test_references_and_literal_line_breaks_are_preserved(self):
        self.assert_formats(r'{1,2}\n%s', r'{1,3}\n%s', False)
        self.assert_formats(r'{1,2}\n%s', '{1,2} %s', False)
        self.assert_formats(r'{1,2}\n%s', r'{1,2}\n%s', True)

    def test_em_dash_fails(self):
        self.write('0001-l049.xml', self.source.replace('Stations', 'A\u2014B'))
        self.assertTrue(any('unsupported em dash' in error for error in self.errors()))

    def test_english_copy_beside_the_neutral_source_fails(self):
        self.write('0001-l044.xml', self.source)
        self.assertIn('0001-l044.xml: English belongs only in 0001.xml; remove this second copy', self.errors())

    def test_language_id_on_the_english_source_fails(self):
        (self.root / '0001.xml').write_text(f'<language id="44">{self.source}</language>', encoding='utf-8')
        self.assertIn('0001.xml: the English source takes no language id', self.errors())

    def test_exemption_covers_only_formatting_of_its_entry(self):
        self.write('0001.xml', '<page id="1"><t id="1">Added %s %s.</t><t id="2">%s</t></page>')
        self.write('0001-l049.xml', '<page id="1"><t id="1">%s Stationen.</t><t id="2">x</t></page>')
        self.exemptions = {('1', '1'): 'noun folded into the sentence'}
        errors = self.errors()
        self.assertEqual(errors, ['0001-l049.xml: page 1, text 2: formatting placeholders, references or line breaks differ'])

    def test_unneeded_exemption_fails(self):
        self.exemptions = {('90210', '1'): 'no longer needed'}
        self.assertEqual(self.errors(), ['translations.json: 90210/1 is exempt but no translation needs it; remove it'])


class ExemptionFileTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def load(self, data):
        (self.root / 'translations.json').write_text(json.dumps(data), encoding='utf-8')
        return translations.load_exemptions(self.root)

    def test_missing_file_means_no_exemptions(self):
        self.assertEqual(translations.load_exemptions(self.root), ({}, []))

    def test_valid_exemptions(self):
        self.assertEqual(self.load({'format_exemptions': {'90210/2010': 'why'}}), ({('90210', '2010'): 'why'}, []))

    def test_reason_and_key_form_are_required(self):
        _, errors = self.load({'format_exemptions': {'90210/2010': ' ', '2010': 'why'}})
        self.assertEqual(len(errors), 2, errors)

    def test_unknown_settings_are_refused(self):
        _, errors = self.load({'format_exemptions': {}, 'languages': [49]})
        self.assertTrue(errors)

    def test_check_reports_exemption_count(self):
        t = self.root / 'src' / 't'
        t.mkdir(parents=True)
        (t / '0001.xml').write_text('<language><page id="1"><t id="1">Added %s %s.</t></page></language>', encoding='utf-8')
        for language in translations.LANGUAGES:
            (t / f'0001-l{language:03d}.xml').write_text(
                f'<language id="{language}"><page id="1"><t id="1">%s.</t></page></language>', encoding='utf-8')
        self.load({'format_exemptions': {'1/1': 'noun folded into the sentence'}})
        errors, summary = translations.check(self.root)
        self.assertEqual(errors, [])
        self.assertIn('1 entries in English and each of 15 translations', summary)
        self.assertIn('1 documented format exemption', summary)


if __name__ == "__main__":
    unittest.main()

