from zope.interface import implements
from zope.i18n import interpolate

from Products.PlacelessTranslationService import getTranslationService
from Products.PlacelessTranslationService.interfaces import \
    IPTSTranslationDomain


class PTSTranslationDomain(object):
    """Makes translation domains that are still kept in PTS available as
    ITranslationDomain utilities. That way they are usable from Zope 3 code
    such as Zope 3 PageTemplates."""

    implements(IPTSTranslationDomain)

    def __init__(self, domain):
        self.domain = domain

    def translate(self, msgid, mapping=None, context=None,
                  target_language=None, default=None):

        pts  = getTranslationService()
        if pts is None or context is None or 'PARENTS' not in context:
            return interpolate(default, mapping)

        parent = context['PARENTS'][-1]
        return pts.translate(self.domain, msgid, mapping, parent,
                             target_language, default)
