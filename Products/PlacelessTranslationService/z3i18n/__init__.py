import ZTUtils, ZPublisher

from Products.PlacelessTranslationService.PlacelessTranslationService \
    import PTSWrapper 

from messageid import MessageID, MessageIDFactory, translate_msgid_with_engine

import patch_TALInterpreter
import patch_MarshallMessageID



old_translate = PTSWrapper.translate
def new_translate(self, domain, *args, **kw):
    # MessageID attributes override arguments
    msgid = args[0]
    if isinstance(msgid, MessageID):
        domain = msgid.domain
        kw['mapping'] = msgid.mapping
        kw['default'] = msgid.default
    return old_translate(self, domain, *args, **kw)

PTSWrapper.translate = new_translate


