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

# BBB
# ignore deprecation warnings on import for now
import warnings
showwarning = warnings.showwarning
warnings.showwarning = lambda *a, **k: None
# these old import should remain here until the TAL and PageTemplate packages
# are completly removed from Zope2
from Products.PageTemplates.PageTemplate import PageTemplate
from TAL.TALInterpreter import TALInterpreter
# restore warning machinery
warnings.showwarning = showwarning

from zope.pagetemplate import pagetemplate
from zope.tal.talinterpreter import TALInterpreter as Z3TALInterpreter

from FasterStringIO import FasterStringIO

def patchedStringIO(self):
    return FasterStringIO()

if hasattr(Z3TALInterpreter, 'StringIO'):
    # Simply patch the StringIO method of TALInterpreter and PageTemplate
    # on a new Zope
    if not Z3TALInterpreter.StringIO is patchedStringIO:
        Z3TALInterpreter.StringIO = patchedStringIO
        pagetemplate.StringIO = patchedStringIO
        TALInterpreter.StringIO = patchedStringIO
        PageTemplate.StringIO = patchedStringIO
