"""
$Id$
"""

class Domain:

    def __init__(self, domain, service):
        self._domain = domain
        self._translationService = service

    def getDomainName(self):
        """Return the domain name"""
        return self._domain

    def translate(self, msgid, mapping=None, context=None,
                  target_language=None):
        return self._translationService.translate(
            self._domain, msgid, mapping, context, target_language)
