# Patch the Zope3 negotiator to cache the negotiated languages
from Products.PlacelessTranslationService.memoize import memoize_second
from zope.i18n.negotiator import Negotiator
Negotiator.getLanguage = memoize_second(Negotiator.getLanguage)


# Patch Zope3 to use a lazy message catalog, but only if we haven't
# restricted the available catalogs in the first place.
from Products.PlacelessTranslationService.load import PTS_LANGUAGES
if PTS_LANGUAGES is None:
    from zope.i18n import gettextmessagecatalog
    from Products.PlacelessTranslationService.lazycatalog import \
        LazyGettextMessageCatalog
    gettextmessagecatalog.GettextMessageCatalog = LazyGettextMessageCatalog
