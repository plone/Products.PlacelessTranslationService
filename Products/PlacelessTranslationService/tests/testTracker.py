# -*- coding: iso-8859-1 -*-
#
# $Id: testTracker.py,v 1.1 2004/07/15 09:19:19 tiran Exp $
#

import os, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

import unittest

from Testing import ZopeTestCase

import Products.PlacelessTranslationService.Tracker as TrackerModule

from Products.PlacelessTranslationService.Tracker import Tracker

ZopeTestCase.installProduct('PlacelessTranslationService')

# Emulate Python 2.3.x
try:
    False
except NameError, e:
    True = not not (1 == 1)
    False = not True


class BasicTrackerTestCase(unittest.TestCase):

    def setUp(self):
        self.tracker = Tracker()
        return

    def testTrackerOff(self):
        """Should be off at stratup
        """
        self.failIf(self.tracker.mode,
                    "Tracker should be off")
        return

    def testDontRecordWhenOff(self):
        """Don't record when tracker is off
        """
        self.tracker.recordFailure('dummy', 'dummy', 'dummy')
        self.failIf(self.tracker.msgids,
                    "There should be no message")
        self.failIf(self.tracker.by_language,
                    "There should be no message")
        return

    def testDontRecordWrongDomain(self):
        """Don't record unwanted domain
        """
        self.tracker.mode = True
        self.tracker.domain = 'foo'
        self.tracker.recordFailure('dummy', 'dummy', 'dummy')
        self.failUnlessEqual(self.tracker.msgids, [])
        self.failUnlessEqual(self.tracker.by_language, {})

    def testRecordOnlyOnce(self):
        """A message should be recorded only once
        """
        self.tracker.mode = True
        self.tracker.domain = 'dummy'
        self.tracker.recordFailure('dummy', 'dummy', 'dummy')
        self.tracker.recordFailure('dummy', 'dummy', 'dummy')
        self.failUnlessEqual(self.tracker.msgids, ['dummy'])
        self.failUnlessEqual(self.tracker.by_language,
                             {'dummy': [0]})
        self.tracker.recordFailure('dummy', 'dummy', 'dummy')
        return

# /class BasicTrackerTestCase

class AdvancedTrackerTestCase(unittest.TestCase):
    """Some testing for data management
    """

    def setUp(self):
        domain = 'foo'
        self.tracker = Tracker()
        self.tracker.mode = True
        self.tracker.domain = domain
        messages = (
            ('msg1', 'fr'),
            ('msg2', 'fr'),
            ('msg1', 'de'),
            ('msg3', 'it'),
            ('msg0', 'it'))
        for msg, lang in messages:
            self.tracker.recordFailure(domain, msg, lang)
        return

    def testavailableLanguages(self):
        """Check all languages recorded for domain
        """
        self.failUnlessEqual(self.tracker.availableLanguages(),
                             ['de', 'fr', 'it'])
        return

    def testAllMessages(self):
        """Checks all recorded messages
        """
        self.failUnlessEqual(self.tracker.availableMsgids(),
                             ['msg0', 'msg1', 'msg2', 'msg3'])
        return

    def testAllMessagesByLanguage(self):
        """Checks all recorded messages for any language
        """
        self.failUnlessEqual(self.tracker.availableMsgids('fr'),
                             ['msg1', 'msg2'])
        self.failUnlessEqual(self.tracker.availableMsgids('de'),
                             ['msg1'])
        self.failUnlessEqual(self.tracker.availableMsgids('it'),
                             ['msg0', 'msg3'])
        return

# /class AdvancedTrackerTestCase

class PTSTrackerTestCase(ZopeTestCase.ZopeTestCase):
    """Testing the tracker through the PlacelessTranslationService
    """

    def afterSetUp(self):
        this_domain = 'PlacelessTranslationService'
        self.ts = self.app.Control_Panel.TranslationService
        package_dir = os.path.dirname(TrackerModule.__file__)
        self.ts._load_i18n_dir(os.path.join(package_dir, 'i18n'))
        self.tracker = self.ts.getTracker()
        self.tracker.mode = True
        self.tracker.domain = this_domain
        messages = (
            ('msg1', 'fr'),
            ('msg2', 'fr'),
            ('msg1', 'de'),
            ('msg3', 'it'),
            ('msg0', 'it'))
        for msg, lang in messages:
            msg = self.ts.translate(this_domain, msg, context=self.folder.REQUEST,
                                    target_language=lang)
        return

    def testAllMessages(self):
        """Checks all recorded messages
        """
        self.failUnlessEqual(self.tracker.availableMsgids(),
                             ['msg0', 'msg1', 'msg2', 'msg3'])
        return

    def testAllMessagesByLanguage(self):
        """Checks all recorded messages for any language
        """
        self.failUnlessEqual(self.tracker.availableMsgids('fr'),
                             ['msg1', 'msg2'])
        self.failUnlessEqual(self.tracker.availableMsgids('de'),
                             ['msg1'])
        self.failUnlessEqual(self.tracker.availableMsgids('it'),
                             ['msg0', 'msg3'])
        return

if __name__ == '__main__':
    framework()
else:
    def test_suite():
        from unittest import TestSuite, makeSuite
        suite = TestSuite()
        suite.addTest(makeSuite(BasicTrackerTestCase))
        suite.addTest(makeSuite(AdvancedTrackerTestCase))
        suite.addTest(makeSuite(PTSTrackerTestCase))
        return suite
