#!/usr/bin/env python
"""Converts a i18n layout to a locales layout

Author: Christian Heimes
License: ZPL 2.1
"""
import os
import os.path
import re
import glob
import shutil

RE_DOMAIN = re.compile(r"\"Domain: ?([a-zA-Z-_]*)\\n\"")
RE_LANGUAGE = re.compile(r"\"Language-code: ?([a-zA-Z-_]*)\\n\"")

base = os.getcwd()
i18n = os.path.join(base, 'i18n')
locales = os.path.join(base, 'locales')
po_files = glob.glob(os.path.join(i18n, '*.po'))

def getLocalsPath(lang, domain):
    po = '%s.po' % domain
    path = os.path.join(locales, lang, 'LC_MESSAGES')
    return path, po

for po in po_files:
    fd = open(po, 'r')
    header = fd.read(5000) # 5,000 bytes should be fine 
    fd.close()
 
    domain = RE_DOMAIN.findall(header)
    lang = RE_LANGUAGE.findall(header)
    if domain and lang:
        domain = domain[0]
        lang = lang[0]
    else:
        print "Failed to get metadata for %s" % po
        continue

    po_path, new_po = getLocalsPath(lang, domain)
    if not os.path.isdir(po_path):
        os.makedirs(po_path)

    shutil.copy(po, os.path.join(po_path, new_po))
    print "Copied %s to %s" % (new_po, po_path)

