#
# PTS test
#

import os, sys

if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

import unittest
from Testing import ZopeTestCase

ZopeTestCase.installProduct('PlacelessTranslationService')

import os
from OFS.Application import get_products
from Products.PlacelessTranslationService import pts_globals, getTranslationService
from Products.PlacelessTranslationService import PlacelessTranslationService as PTS

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
        clv = PTS._class_version
        fsv = getFSVersionTuple()
        for i in range(3):
            self.assertEquals(clv[i], fsv[i],
                              'class version (%s) does not match filesystem version (%s)' % (clv, fsv))


class TestLoadI18NFolder(ZopeTestCase.ZopeTestCase):

    def afterSetUp(self):
        self.wrapper = getTranslationService()
        self.service_path = self.wrapper._path
        self.name = ''.join(self.service_path)
        self.service = self.app.Control_Panel._getOb(self.name)

    def testLoading(self):
        pts_prod = []
        for prod in get_products():
            if prod[1] == 'PlacelessTranslationService':
                pts_prod = prod

        pts_i18n_dir = os.path.join(pts_prod[3], pts_prod[1], 'i18n')
        PTS._load_i18n_dir(self.service, pts_i18n_dir)

        pts_de_name = 'PlacelessTranslationService.i18n-pts-de.po'
        self.failUnless(pts_de_name in self.service.objectIds())
        

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestPTS))
    suite.addTest(makeSuite(TestLoadI18NFolder))
    return suite

if __name__ == '__main__':
    framework()

