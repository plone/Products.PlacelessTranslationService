"""
$Id$
"""

import string
from DocumentTemplate.DT_String import String
from DocumentTemplate.DT_Util import parse_params
import Globals

def get(d, k, f):
    try:
        return d[k]
    except KeyError:
        return f

class TranslateTag:
    """DTML tag equivalent to ZPT's i18n:translate
    """

    # this is the minimal amount of meta-data needed by a DTML Tag.
    name='translate'
    blockContinuations=()
    _msgid = None
    _domain = None

    def __init__(self, blocks):
        self.blocks=blocks
        tname, args, section = blocks[0]
        self.__name__="%s %s" % (tname, args)
        args = parse_params(args, msgid='', domain='')
        if args.has_key('msgid'): self._msgid=args['msgid']
        elif args.has_key(''): self._msgid=args['']
        if args.has_key('domain'): self._domain=args['domain']

    def render(self, md):
        r=[]
        for tname, args, section in self.blocks:
            __traceback_info__=tname
            r.append(section(None, md))

        if r:
            if len(r) > 1: r = "(%s)" % string.join(r,' ')
            else: r = r[0]
        else:
            r = ''

        msgid = self._msgid or r
        domain = self._domain or get(md, 'i18n-domain', 'DTML')

        return translate(domain, msgid, context=md['REQUEST'], default=r)

    __call__=render

def initialize():
    global translate
    from Products.PlacelessTranslationService import translate

    for c in (TranslateTag,):
        String.commands[c.name] = c
