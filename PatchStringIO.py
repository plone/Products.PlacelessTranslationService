# -*- coding: iso-8859-1 -*-

# PATCH 1
#
# Makes REQUEST available from the Globals module.
#
# It's needed because context is not available in the __of__ method,
# so we can't get REQUEST with acquisition. And we need REQUEST for
# local properties (see LocalPropertyManager.pu).
#
# This patch is at the beginning to be sure code that requires it
# doesn't breaks.
#
# This pach is inspired in a similar patch by Tim McLaughlin, see
# "http://dev.zope.org/Wikis/DevSite/Proposals/GlobalGetRequest".
# Thanks Tim!!
#

from thread import get_ident

from ZPublisher import Publish
import Globals

from logging import INFO
from utils import log


def get_request():
    """Get a request object"""
    return Publish._requests.get(get_ident(), None)

def new_publish(request, module_name, after_list, debug=0):
    Publish._requests[get_ident()] = request
    x = Publish.old_publish(request, module_name, after_list, debug)
    try:
        del Publish._requests[get_ident()]
    except KeyError:
        # already deleted?
        pass

    return x

def applyRequestPatch():
    if not hasattr(Publish, '_requests'):
        log('Applying patch', severity=INFO,
            detail='*** Patching ZPublisher.Publish with the get_request patch! ***')
        # Apply patch
        Publish._requests = {}
        Publish.old_publish = Publish.publish
        Publish.publish = new_publish
        Globals.get_request = get_request

applyRequestPatch()

# PATCH 2
#
# Fix uses of StringIO with a Unicode-aware StringIO
#

from Products.PageTemplates.PageTemplate import PageTemplate
from TAL.TALInterpreter import TALInterpreter

patchZ3 = True
try:
    from zope.pagetemplate import pagetemplate
    from zope.tal.talinterpreter import TALInterpreter as Z3TALInterpreter
except ImportError:
    patchZ3 = False

from FasterStringIO import FasterStringIO

if hasattr(TALInterpreter, 'StringIO'):
    # Simply patch the StringIO method of TALInterpreter and PageTemplate
    # on a new Zope
    def patchedStringIO(self):
        return FasterStringIO()
    TALInterpreter.StringIO = patchedStringIO
    PageTemplate.StringIO = patchedStringIO
    if patchZ3:
        Z3TALInterpreter.StringIO = patchedStringIO
        pagetemplate.StringIO = patchedStringIO

# PATCH 3
#
# Fix TAL engine to tolerate mixed Unicode/encoded strings
# This patch will not be included in the next PTS version anymore, as these
# are really a Plone policy decision
#

import textwrap
import warnings

def _unicode_replace(structure):
    if isinstance(structure, str):
        try:
            text = structure.decode('ascii')
        except UnicodeDecodeError:
            try:
                text = structure.decode('utf')
            except UnicodeDecodeError:
                warnings.warn(textwrap.dedent('''\

                *** *** Insertion of non-unicode non-ascii non-utf8 encoded text in TAL is deprecated !!!

                %s...
                ''' % (repr(structure), )), DeprecationWarning, 2)
                # The next line is fool-proof and will substitute ??-s if the
                # encoding was not unicode
                text = structure.decode('utf', 'replace')
    else:
        text = unicode(structure)
    return text

def _nulljoin(valuelist):
    try:
        return ''.join(valuelist)
    except UnicodeDecodeError:
        text = u''
        for value in valuelist:
            text += _unicode_replace(value)
        return text

# Deal with the case where Unicode and encoded strings occur on the same tag.
from TAL import TALInterpreter
TALInterpreter._nulljoin_old = TALInterpreter._nulljoin
TALInterpreter._nulljoin = _nulljoin

if patchZ3:
    from zope.tal import talinterpreter
    talinterpreter._nulljoin_old = talinterpreter._nulljoin
    talinterpreter._nulljoin = _nulljoin


# PATCH 4
#
# Another fix for TAL engine to tolerate mixed Unicode/encoded strings
# Fixes issue #6238
#

from TAL.TALInterpreter import BOOLEAN_HTML_ATTRS
from TAL.TALDefs import attrEscape
import cgi

def patched_attrAction_tal(self, item):
    name, value, action = item[:3]
    ok = 1
    expr, xlat, msgid = item[3:]
    if self.html and name.lower() in BOOLEAN_HTML_ATTRS:
        evalue = self.engine.evaluateBoolean(item[3])
        if evalue is self.Default:
            if action == 'insert': # Cancelled insert
                ok = 0
        elif evalue:
            value = None
        else:
            ok = 0
    elif expr is not None:
        evalue = self.engine.evaluateText(item[3])
        if evalue is self.Default:
            if action == 'insert': # Cancelled insert
                ok = 0
        else:
            if evalue is None:
                ok = 0
            value = evalue
    else:
        evalue = None

    if ok:
        if xlat:
            translated = self.translate(msgid or value, value, {})
            if translated is not None:
                value = translated
        if value is None:
            value = name
        elif evalue is self.Default:
            value = attrEscape(value)
        else:
            value = cgi.escape(value, quote=1)
        # use _nulljoin defined in this module (PTS/PatchStringIO.py)
        value = _nulljoin((name, '=', '"%s"' % value))
    return ok, name, value

# Deal with the another case where Unicode and encoded strings occur on the same tag.
# This one (in the attrAction_tal) is raised when page template contains non ascii string
from TAL.TALInterpreter import TALInterpreter
TALInterpreter.attrAction_tal_old = TALInterpreter.attrAction_tal
TALInterpreter.attrAction_tal = patched_attrAction_tal
TALInterpreter.bytecode_handlers_tal_old = TALInterpreter.bytecode_handlers_tal
TALInterpreter.bytecode_handlers_tal["<attrAction>"] = TALInterpreter.attrAction_tal
