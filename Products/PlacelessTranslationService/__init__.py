"""
$Id$
"""

import os

from Products.PageTemplates.GlobalTranslationService import \
    setGlobalTranslationService, getGlobalTranslationService
import Globals
pts_globals = globals()

from OFS.Application import get_products
from AccessControl import ModuleSecurityInfo, allow_module
from AccessControl.Permissions import view

import PatchStringIO # patch at first
from PlacelessTranslationService import PlacelessTranslationService
from PlacelessTranslationService import PTSWrapper
from PlacelessTranslationService import PTS_IS_RTL

import logging
from utils import log

from Negotiator import negotiator, setCookieLanguage
import TranslateTags
from GettextMessageCatalog import purgeMoFileCache

# this is for packages that need to initialize stuff after we're done
notify_initialized = []

# id to use in the Control Panel
cp_id = 'TranslationService'

# module level translation service
translation_service = None

# icon
misc_ = {
    'PlacelessTranslationService.png':
    Globals.ImageFile('www/PlacelessTranslationService.png', globals()),
    'GettextMessageCatalog.png':
    Globals.ImageFile('www/GettextMessageCatalog.png', globals()),
    }

# set product-wide attrs for importing
security = ModuleSecurityInfo('Products.PlacelessTranslationService')
allow_module('Products.PlacelessTranslationService')

security.declareProtected(view, 'getTranslationService')
def getTranslationService():
    """returns the PTS instance
    """
    return translation_service

security.declareProtected(view, 'translate')
def translate(*args, **kwargs):
    """see PlaceslessTranslationService.PlaceslessTranslationService
    """
    return getTranslationService().translate(*args, **kwargs)

security.declareProtected(view, 'utranslate')
def utranslate(*args, **kwargs):
    """see PlaceslessTranslationService.PlaceslessTranslationService
    """
    return getTranslationService().utranslate(*args, **kwargs)

security.declareProtected(view, 'getLanguages')
def getLanguages(*args, **kwargs):
    """see PlaceslessTranslationService.PlaceslessTranslationService
    """
    return getTranslationService().getLanguages(*args, **kwargs)

security.declareProtected(view, 'getLanguageName')
def getLanguageName(*args, **kwargs):
    """see PlaceslessTranslationService.PTSWrapper
    """
    return getTranslationService().getLanguageName(*args, **kwargs)

security.declareProtected(view, 'isRTL')
def isRTL(context, domain):
    """Returns true for a rtl language and false for a ltr language
    """
    return getTranslationService().isRTL(context, domain)

security.declareProtected(view, 'setCookieLanguage')
# imported from the Negotiator

negotiateDeprecatedLogged = 0
security.declareProtected(view, 'negotiate')
def negotiate(langs, context):
    """ deprecated! """
    if not negotiateDeprecatedLogged:
        log('Products.PlacelessTranslationService.negotiate() is deprecated', logging.WARNING)
        negotiateDeprecatedLogged = 1
    return negotiator.negotiate(langs, context, 'language')

def make_translation_service(cp):
    """Control_Panel translation service
    """
    global translation_service
    translation_service = PlacelessTranslationService('default')
    translation_service.id = cp_id
    cp._setObject(cp_id, translation_service)
    translation_service = PTSWrapper(translation_service)
    return getattr(cp, cp_id)

def initialize(context):
    # hook into the Control Panel
    global translation_service

    # allow for disabling PTS entirely by setting a environment variable.
    if bool(os.getenv('DISABLE_PTS')):
        log('Disabled by environment variable "DISABLE_PTS".', logging.WARNING)
        return

    cp = context._ProductContext__app.Control_Panel # argh
    if cp_id in cp.objectIds():
        cp_ts = getattr(cp, cp_id)
        # use the ts in the acquisition context of the control panel
        # translation_service = translation_service.__of__(cp)
        translation_service = PTSWrapper(cp_ts)
    else:
        cp_ts = make_translation_service(cp)

    # don't touch - this is the last version that didn't have the
    # attribute (0.4)
    instance_version = getattr(cp_ts, '_instance_version', (0, 4, 0, 0))
    if instance_version[3] > 99:
        log('development mode: translation service recreated',
            detail = '(found %s.%s.%s.%s)\n' % instance_version)
        cp._delObject(cp_id)
        cp_ts = make_translation_service(cp)

    if instance_version < PlacelessTranslationService._class_version:
        log('outdated translation service found, recreating',
            detail = '(found %s.%s.%s.%s)\n' % instance_version)
        cp._delObject(cp_id)
        purgeMoFileCache()
        cp_ts = make_translation_service(cp)

    # sweep products
    log('products: %r' % get_products(), logging.DEBUG)
    for prod in get_products():
        # prod is a tuple in the form:
        # (priority, dir_name, index, base_dir) for each Product directory
        cp_ts._load_i18n_dir(os.path.join(prod[3], prod[1], 'i18n'))
        cp_ts._load_locales_dir(os.path.join(prod[3], prod[1], 'locales'))

    # sweep the i18n directory for local catalogs
    instance_i18n = os.path.join(INSTANCE_HOME, 'i18n')
    if os.path.isdir(instance_i18n):
        cp_ts._load_i18n_dir(instance_i18n)

    instance_locales = os.path.join(INSTANCE_HOME, 'locales')
    if os.path.isdir(instance_locales):
        cp_ts._load_locales_dir(instance_locales)

    # didn't found any catalogs
    if not cp_ts.objectIds():
        log('no translations found!', logging.DEBUG)

    # set ZPT's translation service
    # NOTE: since this registry is a global var we cant register the
    #       persistent service itself (zodb connection) therefore a
    #       wrapper is created around it
    setGlobalTranslationService(PTSWrapper(cp_ts))

    # notify anyone who needs it
    TranslateTags.initialize()
    for function in notify_initialized:
        function()
