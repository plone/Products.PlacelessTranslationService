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


# Patch the Zope3 i18n zcml statement to compile po files to mo
from zope.i18n import zcml
from Products.PlacelessTranslationService.load import _compile_locales_dir

def wrap_compile_translations(func):
    def compile_translations(*args, **kwargs):
        if 'directory' in kwargs:
            _compile_locales_dir(kwargs.get('directory'))
        func(*args, **kwargs)
    return compile_translations

# Apply patch
zcml.registerTranslations = wrap_compile_translations(zcml.registerTranslations)
