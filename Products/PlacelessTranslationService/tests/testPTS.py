#
# PTS test
#

import os, sys

if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

import unittest
from Testing import ZopeTestCase

ZopeTestCase.installProduct('PlacelessTranslationService')

from Products.PlacelessTranslationService import pts_globals
from Products.PlacelessTranslationService import PlacelessTranslationService

from Globals import package_home
PACKAGE_HOME = package_home(pts_globals)

from Products.CMFPlone.utils import versionTupleFromString

def getFSVersionTuple():
    """Reads version.txt and returns version tuple"""
    vfile = "%s/version.txt" % PACKAGE_HOME
    v_str = open(vfile, 'r').read().lower()
    return versionTupleFromString(v_str)


class TestPTS(ZopeTestCase.ZopeTestCase):

    def afterSetUp(self):
        pass

    def testClassVersion(self):
        clv = PlacelessTranslationService._class_version
        fsv = getFSVersionTuple()
        for i in range(3):
            self.assertEquals(clv[i], fsv[i],
                              'class version (%s) does not match filesystem version (%s)' % (clv, fsv))


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestPTS))
    return suite

if __name__ == '__main__':
    framework()

