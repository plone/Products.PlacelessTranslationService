#
# PTS test
#

import os, sys

if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

import unittest
from Testing import ZopeTestCase

ZopeTestCase.installProduct('PlacelessTranslationService')

from DocumentTemplate.DT_HTML import HTML
from DocumentTemplate.DT_String import String

from Products.PlacelessTranslationService import getTranslationService
from Products.PlacelessTranslationService.Negotiator import registerLangPrefsMethod

class DePTS:
    def __init__(self, context):
        """A preference hook for PTS that enforces german translation."""
        return None

    def getPreferredLanguages(self):
        """Returns the list of the bound languages."""
        return ['de']

registerLangPrefsMethod({'klass':DePTS, 'priority':200 })

class TestDTML(ZopeTestCase.ZopeTestCase):

    def afterSetUp(self):
        self.wrapper = getTranslationService()
        self.name = ''.join(self.wrapper._path)
        self.service = self.app.Control_Panel._getOb(self.name)

    def testSimpleString(self):
        html = String("Hello %(name)s")
        res = html(name='world')
        expected = 'Hello world'
        self.assertEquals(res, expected)

    def testSimpleFile(self):
        html = HTML("Hello <dtml-var name>")
        res = html(name='world')
        expected = 'Hello world'
        self.assertEquals(res, expected)

    def testTranslateCommand(self):
        # test if the translate command has been successfully registered
        self.failUnless('translate' in String.commands)

    def testDirectTranslate(self):
        res = self.service.translate('PlacelessTranslationService',
                                     'Reload this catalog',
                                     context=self.app)
        expected = 'Diesen Katalog neu einlesen'
        self.assertEquals(res, expected)

    def testString(self):
        # simple string which we do not expect to be translated
        html = String("%(translate domain=pts)[untranslated text%(translate domain=pts)]")
        expected = 'untranslated text'
        self.assertEquals(html(REQUEST=[]), expected)

        # string which should be translated, as tested in the above direct test
        html = String("%(translate domain=PlacelessTranslationService)[Reload this catalog%(translate domain=PlacelessTranslationService)]")
        expected = 'Diesen Katalog neu einlesen'
        self.assertEquals(html(self.app.REQUEST), expected)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestDTML))
    return suite

if __name__ == '__main__':
    framework()

