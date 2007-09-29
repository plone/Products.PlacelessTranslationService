import fnmatch
import logging
import os
from os.path import isdir
from os.path import join
import shutil
from stat import ST_MTIME

from pythongettext.msgfmt import Msgfmt
from zope.component import getGlobalSiteManager
from zope.component import queryUtility
from zope.i18n.gettextmessagecatalog import GettextMessageCatalog
from zope.i18n.interfaces import ITranslationDomain
from zope.i18n.translationdomain import TranslationDomain

from Products.PlacelessTranslationService.utils import log


def _load_i18n_dir(basepath):
    """
    Loads an i18n directory (Zope3 PTS format)
    Format:
        Products/MyProduct/i18n/*.po
    The language and domain are stored in the po file
    """
    if not isdir(basepath):
        return

    # load po files
    basepath = os.path.normpath(basepath)
    names = fnmatch.filter(os.listdir(basepath), '*.po')
    if not names:
        log('Nothing found in ' + basepath, logging.DEBUG)
        return
    registered = []
    for name in names:
        lang = None
        domain = None
        pofile = join(basepath, name)
        # XXX Only parse the header and not the whole file
        po = Msgfmt(pofile, None)
        po.read()
        header = po.messages.get('', None)
        if header is not None:
            mime_header = {}
            pairs = [l.split(':', 1) for l in header.split('\n') if l]
            for key, value in pairs:
                mime_header[key.strip().lower()] = value.strip()
            lang = mime_header.get('language-code', None)
            domain = mime_header.get('domain', None)
            if lang is not None and domain is not None:
                _register_catalog_file(name, basepath, lang, domain, True)
                registered.append(name)

    log('Initialized:', detail = str(len(registered)) +
        (' message catalogs in %s\n' % basepath))

def _updateMoFile(name, msgpath, lang, domain):
    """
    Creates or updates a mo file in the locales folder. Returns True if a
    new file was created.
    """
    pofile = os.path.normpath(join(msgpath, name))
    mofile = os.path.normpath(join(msgpath, os.path.splitext(name)[0]+'.mo'))
    create = False
    update = False

    try:
        po_mtime = os.stat(pofile)[ST_MTIME]
    except (IOError, OSError):
        po_mtime = 0

    if os.path.exists(mofile):
        # Update mo file?
        try:
            mo_mtime = os.stat(mofile)[ST_MTIME]
        except (IOError, OSError):
            mo_mtime = 0

        if po_mtime > mo_mtime:
            # Update mo file
            update = True
        else:
            # Mo file is current
            return
    else:
        # Create mo file
        create = True

    if create or update:
        try:
            mo = Msgfmt(pofile, domain).getAsFile()
            fd = open(mofile, 'wb')
            fd.write(mo.read())
            fd.close()

        except (IOError, OSError):
            log('Error while compiling %s' % pofile, logging.WARNING)
            return

        if create:
            return True

    return None

def _register_catalog_file(name, msgpath, lang, domain, update=False):
    """Registers a catalog file as an ITranslationDomain."""
    result = _updateMoFile(name, msgpath, lang, domain)
    if result or update:
        # Newly created file or one from a i18n folder,
        # the Z3 domain utility does not exist
        mofile = join(msgpath, os.path.splitext(name)[0] + '.mo')
        if queryUtility(ITranslationDomain, name=domain) is None:
            ts_domain = TranslationDomain(domain)
            sm = getGlobalSiteManager()
            sm.registerUtility(ts_domain, ITranslationDomain, name=domain)

        util = queryUtility(ITranslationDomain, name=domain)
        if util is not None and os.path.exists(mofile):
            # Add message catalog
            cat = GettextMessageCatalog(lang, domain, mofile)
            util.addCatalog(cat)

def _load_locales_dir(basepath):
    """
    Loads an locales directory (Zope3 format)
    Format:
        Products/MyProduct/locales/${lang}/LC_MESSAGES/${domain}.po
    Where ${lang} and ${domain} are the language and the domain of the po
    file (e.g. locales/de/LC_MESSAGES/plone.po)
    """
    found=[]
    if not isdir(basepath):
        return
    for lang in os.listdir(basepath):
        langpath = join(basepath, lang)
        if not isdir(langpath):
            # it's not a directory
            continue
        msgpath = join(langpath, 'LC_MESSAGES')
        if not isdir(msgpath):
            # it doesn't contain a LC_MESSAGES directory
            continue
        names = fnmatch.filter(os.listdir(msgpath), '*.po')
        for name in names:
            domain = name[:-3]
            found.append('%s:%s' % (lang, domain))
            _register_catalog_file(name, msgpath, lang, domain)

    if not found:
        log('Nothing found in ' + basepath, logging.DEBUG)
        return
    log('Initialized:', detail = str(len(found)) +
        (' message catalogs in %s\n' % basepath))

def _remove_mo_cache(path=None):
    """Remove the mo cache."""
    if path is not None and os.path.exists(path):
        if not os.access(path, os.W_OK):
            log("No write permission on folder %s" % path, logging.INFO)
            return False
        shutil.rmtree(path)
