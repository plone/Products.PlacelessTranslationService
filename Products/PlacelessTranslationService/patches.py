import os

# Patch the Zope3 negotiator to cache the negotiated languages
from Products.PlacelessTranslationService.memoize import memoize_second
from zope.i18n.negotiator import Negotiator
Negotiator.getLanguage = memoize_second(Negotiator.getLanguage)


# Patch Zope3 to use a lazy message catalog, but only if we haven't
# restricted the available catalogs in the first place.
from Products.PlacelessTranslationService.load import PTS_LANGUAGES
if PTS_LANGUAGES is not None:
    from zope.i18n import gettextmessagecatalog
    from Products.PlacelessTranslationService.lazycatalog import \
        LazyGettextMessageCatalog
    gettextmessagecatalog.GettextMessageCatalog = LazyGettextMessageCatalog


# Patch the Zope3 i18n zcml statement:
#	- to compile po files to mo
#	- to check for an existing domain

from zope.i18n import zcml
from Products.PlacelessTranslationService.load import _compile_locales_dir

from zope.i18n.gettextmessagecatalog import GettextMessageCatalog
from zope.i18n.testmessagecatalog import TestMessageCatalog
from zope.i18n.translationdomain import TranslationDomain
from zope.i18n.interfaces import ITranslationDomain

from zope.component import queryUtility
from zope.component.zcml import utility

def patched_registerTranslations(_context, directory):

    # compile mo files
    _compile_locales_dir(directory)  
    path = os.path.normpath(directory)
    domains = {}
    for language in os.listdir(path):
        lc_messages_path = os.path.join(path, language, 'LC_MESSAGES')
        if os.path.isdir(lc_messages_path):
            for domain_file in os.listdir(lc_messages_path):
                if domain_file.endswith('.mo'):
                    domain_path = os.path.join(lc_messages_path, domain_file)
                    domain = domain_file[:-3]
                    if not domain in domains:
                        domains[domain] = {}
                    domains[domain][language] = domain_path

    # Now create TranslationDomain objects and add them as utilities
    for name, langs in domains.items():
        # Try to get an existing domain and add catalogs to it
        domain = queryUtility(ITranslationDomain, name)
        
        if domain is None:
            domain = TranslationDomain(name)

        for lang, file in langs.items():
            domain.addCatalog(GettextMessageCatalog(lang, name, file))

        # make sure we have a TEST catalog for each domain:
        domain.addCatalog(TestMessageCatalog(name))
        utility(_context, ITranslationDomain, domain, name=name)

# applying the patch
zcml.registerTranslations = patched_registerTranslations

