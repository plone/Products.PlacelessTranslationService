import sys

import unittest

from StringIO import StringIO

from TAL.TALDefs import I18NError
from TAL.tests.test_talinterpreter import TestCaseBase
from TAL.TALInterpreter import TALInterpreter
from TAL.DummyEngine import DummyEngine, Default
from DocumentTemplate.DT_Util import ustr

from Products.PlacelessTranslationService.z3i18n import patch_TALInterpreter
from Products.PlacelessTranslationService.z3i18n.messageid import MessageID

class Z3DummyEngine(DummyEngine):
    
    def evaluateText(self, expr):
        text = self.evaluate(expr)
        if text is not None and text is not Default and not isinstance(text, MessageID):
            text = ustr(text)
        return text

class Z3I18NCornerTestCase(TestCaseBase):

    def setUp(self):
        self.engine = Z3DummyEngine()
        self.engine.setLocal('bar', 'BaRvAlUe')
        self.engine.setLocal('msg', MessageID('MsGiD', 'domain'))

    def _check(self, program, expected):
        result = StringIO()
        self.interpreter = TALInterpreter(program, {}, self.engine,
                                          stream=result)
        self.interpreter()
        self.assertEqual(expected, result.getvalue())

    def test_content_with_messageid_and_i18nname_and_i18ntranslate(self):
        # Let's tell the user this is incredibly silly!
        self.assertRaises(
            I18NError, self._compile,
            '<span i18n:translate="" tal:content="bar" i18n:name="bar_name"/>')

    def test_content_with_plaintext_and_i18nname_and_i18ntranslate(self):
        # Let's tell the user this is incredibly silly!
        self.assertRaises(
            I18NError, self._compile,
            '<span i18n:translate="" i18n:name="color_name">green</span>')

    def test_translate_static_text_as_dynamic(self):
        program, macros = self._compile(
            '<div i18n:translate="">This is text for '
            '<span i18n:translate="" tal:content="bar" i18n:name="bar_name"/>.'
            '</div>')
        self._check(program,
                    '<div>THIS IS TEXT FOR <span>BARVALUE</span>.</div>\n')

    def test_translate_messageid(self):
        program, macros = self._compile('<span tal:content="msg" />')
        self._check(program,
                    '<span>MSGID</span>\n')


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(Z3I18NCornerTestCase))
    return suite


if __name__ == "__main__":
    errs = utils.run_suite(test_suite())
    sys.exit(errs and 1 or 0)
