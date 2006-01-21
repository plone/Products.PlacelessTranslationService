##############################################################################
#    Copyright (C) 2001-2005 Lalo Martins <lalo@laranja.org>,
#                  Zope Corporation and Contributors

#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307, USA
"""Placeless Translation Service for providing I18n to file-based code.

$Id$
"""

import sys, os, re, fnmatch
from types import DictType, StringType, UnicodeType

import Globals
from ExtensionClass import Base
from Acquisition import ImplicitAcquisitionWrapper
from AccessControl import ClassSecurityInfo
from AccessControl.Permissions import view, view_management_screens
from Globals import InitializeClass
from OFS.Folder import Folder
from ZPublisher.HTTPRequest import HTTPRequest

from GettextMessageCatalog import BrokenMessageCatalog
from GettextMessageCatalog import GettextMessageCatalog
from GettextMessageCatalog import translationRegistry
from GettextMessageCatalog import rtlRegistry
from GettextMessageCatalog import getMessage
from Negotiator import negotiator
from Domain import Domain
from utils import log, Registry, INFO, BLATHER, PROBLEM
from msgfmt import PoSyntaxError

from Tracker import global_tracker
from GettextMessageCatalog import ptFile

PTS_IS_RTL = '_pts_is_rtl'

try:
    from pax import XML
except:
    def XML(v):
        return str(v)

_marker = []

def map_get(map, name):
    return map.get(name)

# Setting up some regular expressions for finding interpolation variables in
# the text.
NAME_RE = r"[a-zA-Z][a-zA-Z0-9_]*"
_interp_regex = re.compile(r'(?<!\$)(\$(?:%(n)s|{%(n)s}))' %({'n': NAME_RE}))
_get_var_regex = re.compile(r'%(n)s' %({'n': NAME_RE}))


# The configure.zcml file should specify a list of fallback languages for the
# site.  If a particular catalog for a negotiated language is not available,
# then the zcml specified order should be tried.  If that fails, then as a
# last resort the languages in the following list are tried.  If these fail
# too, then the msgid is returned.
#
# Note that these fallbacks are used only to find a catalog.  If a particular
# message in a catalog is not translated, tough luck, you get the msgid.
LANGUAGE_FALLBACKS = list(os.environ.get('LANGUAGE_FALLBACKS', 'en').split(' '))

catalogRegistry = Registry()
registerCatalog = catalogRegistry.register
fbcatalogRegistry = Registry()
registerFBCatalog = fbcatalogRegistry.register


class PTSWrapper(Base):
    """
    Wrap the persistent PTS since persistent
    objects cant be passed around threads
    """

    security = ClassSecurityInfo()

    def __init__(self, service):
        # get path from service
        self._path=service.getPhysicalPath()

    security.declarePrivate('load')
    def load(self, context):
        # return the real service
        try: root = context.getPhysicalRoot()
        except: return None
        # traverse the service
        return root.unrestrictedTraverse(self._path, None)

    security.declareProtected(view, 'translate')
    def translate(self, domain, msgid, mapping=None, context=None,
                  target_language=None, default=None):
        """
        translate a message using the default encoding
        get the real service and call its translate method
        return default if service couldnt be retrieved
        """

        # this is useful for GettextMessageCatalog
        # see the end of GettextMessageCatalog.py for details
        __pts_caller_backcount__ = 1

        service = self.load(context)
        if not service: return default
        return service.translate(domain, msgid, mapping, context, target_language, default)

    security.declareProtected(view, 'utranslate')
    def utranslate(self, domain, msgid, mapping=None, context=None,
                  target_language=None, default=None):
        """
        translate a message using unicode
        see translate()
        """
        service = self.load(context)
        if not service: return default
        return service.utranslate(domain, msgid, mapping, context, target_language, default)

    security.declarePublic(view, 'getLanguageName')
    def getLanguageName(self, code, context):
        service = self.load(context)
        return service.getLanguageName(code)

    security.declarePublic(view, 'getLanguages')
    def getLanguages(self, context, domain=None):
        service = self.load(context)
        return service.getLanguages(domain)

    security.declarePrivate('negotiate_language')
    def negotiate_language(self, context, domain):
        service = self.load(context)
        return service.negotiate_language(context.REQUEST,domain)

    security.declarePublic('isRTL')
    def isRTL(self, context, domain):
        service = self.load(context)
        # Default to LtR
        if service is None: return False
        return service.isRTL(context.REQUEST,domain)

    def __repr__(self):
        """
        return a string representation
        """
        return "<PTSWrapper for %s>" % '/'.join(self._path)

InitializeClass(PTSWrapper)

class PlacelessTranslationService(Folder):
    """
    The Placeless Translation Service
    """

    meta_type = title = 'Placeless Translation Service'
    icon = 'misc_/PlacelessTranslationService/PlacelessTranslationService.png'
    # major, minor, patchlevel, internal
    # internal is always 0 on releases
    # if you hack this internally, increment it
    # -3 for alpha, -2 for beta, -1 for release candidate
    # for forked releases internal is always 99
    # use an internal of > 99 to recreate the PTS at every startup
    # (development mode)
    _class_version = (1, 2, 6, 0)
    all_meta_types = ()

    manage_options = Folder.manage_options + (
        {'label': 'Tracker', 'action': 'manage_trackerForm'},)

    manage_trackerForm = ptFile(
        'manage_trackerForm', globals(), 'www', 'manage_trackerForm')

    security = ClassSecurityInfo()

    def __init__(self, default_domain='global', fallbacks=None):
        self._instance_version = self._class_version
        # XXX We haven't specified that ITranslationServices have a default
        # domain.  So far, we've required the domain argument to .translate()
        self._domain = default_domain
        # _catalogs maps (language, domain) to identifiers
        catalogRegistry = {}
        fbcatalogRegistry = {}
        # What languages to fallback to, if there is no catalog for the
        # requested language (no fallback on individual messages)
        if fallbacks is None:
            fallbacks = LANGUAGE_FALLBACKS
        self._fallbacks = fallbacks

    def _registerMessageCatalog(self, catalog):
        # dont register broken message catalogs
        if isinstance(catalog, BrokenMessageCatalog): return

        domain = catalog.getDomain()
        catalogRegistry.setdefault((catalog.getLanguage(), domain), []).append(catalog.getIdentifier())
        for lang in catalog.getOtherLanguages():
            fbcatalogRegistry.setdefault((lang, domain), []).append(catalog.getIdentifier())
        self._p_changed = 1

    def _unregister_inner(self, catalog, clist):
        for key, combo in clist.items():
            try:
                combo.remove(catalog.getIdentifier())
            except ValueError:
                continue
            if not combo: # removed the last catalog for a
                          # language/domain combination
                del clist[key]

    def _unregisterMessageCatalog(self, catalog):
        self._unregister_inner(catalog, catalogRegistry)
        self._unregister_inner(catalog, fbcatalogRegistry)
        self._p_changed = 1

    security.declarePrivate('calculatePoId')
    def calculatePoId(self, name, popath, language=None, domain=None):
        """Calulate the po id
        """
        # instance, software and global catalog path for i18n and locales
        iPath       = os.path.join(INSTANCE_HOME, 'Products') + os.sep
        sPath       = os.path.join(SOFTWARE_HOME, 'Products') + os.sep
        gci18nNPath = os.path.join(INSTANCE_HOME, 'i18n')
        gcLocPath   = os.path.join(INSTANCE_HOME, 'locales')

        # a global catalog is
        isGlobalCatalog = False

        # remove [isg]Path from the popath
        if popath.startswith(iPath):
            path = popath[len(iPath):]
        elif popath.startswith(sPath):
            path = popath[len(sPath):]
        elif popath.startswith(gci18nNPath):
            path = popath[len(gci18nNPath):]
            isGlobalCatalog = True
        elif popath.startswith(gcLocPath):
            path = popath[len(gcLocPath):]
            isGlobalCatalog = True
        else:
            # po file is located at a strange place
            # calculate the name using the position of the
            # i18n/locales directory
            p = popath.split(os.sep)
            try:
                idx = p.index('i18n')
            except ValueError:
                try:
                    idx = p.index('locales')
                except ValueError:
                    raise OSError('Invalid po path %s for %s. That should not happen' % (popath, name))
            path = os.path.join(p[idx-1],p[idx])

        # the po file name is GlobalCatalogs-$name or MyProducts.i18n-$name
        # or MyProducts.locales-$name
        if not isGlobalCatalog:
            p = path.split(os.sep)
            pre = '.'.join(p[:2])
        else:
            pre = 'GlobalCatalogs'

        if language and domain:
            return "%s-%s-%s.po" % (pre, language, domain)
        else:
            return '%s-%s' % (pre, name)

    def _load_catalog_file(self, name, popath, language=None, domain=None):
        """
        create catalog instances in ZODB
        """

        id = self.calculatePoId(name, popath, language=language, domain=domain)

        # validate id
        try: self._checkId(id, 1)
        except: id=name # fallback mode for borked paths

        # the po file path
        pofile = os.path.join(popath, name)

        ob = self._getOb(id, _marker)
        try:
            if isinstance(ob, BrokenMessageCatalog):
                # remove broken catalog
                self._delObject(id)
                ob = _marker
        except: pass
        try:
            if ob is _marker:
                self.addCatalog(GettextMessageCatalog(id, pofile, language, domain))
            else:
                self.reloadCatalog(ob)
        except IOError:
            # io error probably cause of missing or
            # not accessable
            try:
                # remove false catalog from PTS instance
                self._delObject(id)
            except:
                pass
        except KeyboardInterrupt:
            raise
        except:
            exc=sys.exc_info()
            log('Message Catalog has errors', PROBLEM, name, exc)
            self.addCatalog(BrokenMessageCatalog(id, pofile, exc))

    def _load_i18n_dir(self, basepath):
        """
        Loads an i18n directory (Zope3 PTS format)
        Format:
            Products/MyProduct/i18n/*.po
        The language and domain are stored in the po file
        """
        log('looking into ' + basepath, BLATHER)
        if not os.path.isdir(basepath):
            log('it does not exist', BLATHER)
            return

        # print deprecation warning for mo files
        depr_names = fnmatch.filter(os.listdir(basepath), '*.mo')
        if depr_names:
            import warnings
            warnings.warn(
                'Compiled po files (*.mo) found in %s. '
                'PlacelessTranslationService now compiles '
                'mo files automatically. All mo files have '
                'been ignored.' % basepath, DeprecationWarning, stacklevel=4)

        # load po files
        names = fnmatch.filter(os.listdir(basepath), '*.po')
        if not names:
            log('nothing found', BLATHER)
            return
        for name in names:
            self._load_catalog_file(name, basepath)

        log('Initialized:', detail = repr(names) + (' from %s\n' % basepath))

    def _load_locales_dir(self, basepath):
        """
        Loads an locales directory (Zope3 format)
        Format:
            Products/MyProduct/locales/${lang}/LC_MESSAGES/${domain}.po
        Where ${lang} and ${domain} are the language and the domain of the po
        file (e.g. locales/de/LC_MESSAGES/plone.po)
        """
        found=[]
        log('looking into ' + basepath, BLATHER)
        if not os.path.isdir(basepath):
            log('it does not exist', BLATHER)
            return

        for lang in os.listdir(basepath):
            langpath = os.path.join(basepath, lang)
            if not os.path.isdir(langpath):
                # it's not a directory
                continue
            msgpath = os.path.join(langpath, 'LC_MESSAGES')
            if not os.path.isdir(msgpath):
                # it doesn't contain a LC_MESSAGES directory
                continue
            names = fnmatch.filter(os.listdir(msgpath), '*.po')
            for name in names:
                domain = name[:-3]
                found.append('%s:%s' % (lang, domain))
                self._load_catalog_file(name, msgpath, lang, domain)

        if not found:
            log('nothing found', BLATHER)
            return
        log('Initialized:', detail = repr(found) + (' from %s\n' % basepath))

    def _getContext(self, context):
        # ZPT passes the object as context.  That's wrong according to spec.
        context = getattr(context, 'REQUEST', context)
        if not isinstance(context, HTTPRequest):
            # try to recover
            log('Using get_request patch.', severity=INFO)
            # XXX: import the get_request method
            # this will fail the first time we need it if the patch
            # wasn't applied before
            try:
                from Globals import get_request
            except ImportError:
                from PatchStringIO import applyRequestPatch
                applyRequestPatch()
            else:
                context = get_request()

        return context

    security.declareProtected(view_management_screens, 'manage_renameObject')
    def manage_renameObject(self, id, new_id, REQUEST=None):
        """
        wrap manage_renameObject to deal with registration
        """
        catalog = self._getOb(id)
        self._unregisterMessageCatalog(catalog)
        Folder.manage_renameObject(self, id, new_id, REQUEST=None)
        self._registerMessageCatalog(catalog)

    def _delObject(self, id, dp=1):
        catalog = self._getOb(id)
        Folder._delObject(self, id, dp)
        self._unregisterMessageCatalog(catalog)

    security.declarePrivate('reloadCatalog')
    def reloadCatalog(self, catalog):
        # trigger an exception if we don't know anything about it
        id=catalog.id
        self._getOb(id)
        self._unregisterMessageCatalog(catalog)
        catalog.reload()
        catalog=self._getOb(id)
        self._registerMessageCatalog(catalog)

    security.declarePrivate('addCatalog')
    def addCatalog(self, catalog):
        try:
            self._delObject(catalog.id)
        except:
            pass
        self._setObject(catalog.id, catalog, set_owner=False)
        log('adding %s: %s' % (catalog.id, catalog.title))
        self._registerMessageCatalog(catalog)

    security.declarePrivate('getCatalogsForTranslation')
    def getCatalogsForTranslation(self, context, domain, target_language=None):
        # ZPT passes the object as context.  That's wrong according to spec.
        context = self._getContext(context)

        if target_language is None:
            target_language = self.negotiate_language(context, domain)

        # cache catalog names to speed up because this method is called
        # for every msgid
        cache_name = '_pts_catalog_names_%s_%s' % (domain, target_language or 'none')
        cached_catalog_names = context.get(cache_name, None)
        if cached_catalog_names:
            return [translationRegistry[name] for name in cached_catalog_names]

        # get the catalogs for translations
        catalog_names = catalogRegistry.get((target_language, domain), ()) or \
                        fbcatalogRegistry.get((target_language, domain), ())
        catalog_names = list(catalog_names)

        # get fallback catalogs
        for language in self._fallbacks:
            fallback_catalog_names = catalogRegistry.get((language, domain),  ())
            if fallback_catalog_names:
                for fallback_catalog_name in fallback_catalog_names:
                    if fallback_catalog_name not in catalog_names:
                        catalog_names.append(fallback_catalog_name)

        # move global catalogs to the beginning to allow overwriting
        # message ids by placing a po file in INSTANCE_HOME/i18n
        # use pos to keep the sort order
        pos=0
        for i in range(len(catalog_names)):
            catalog_name = catalog_names[i]
            if catalog_name.startswith('GlobalCatalogs-'):
                del catalog_names[i]
                catalog_names.insert(pos, catalog_name)
                pos+=1

        # set catalog names cache. Do *not* store a persistent object
        # in the request. It may cause reference circles and cause memory leaks
        context.set(cache_name, catalog_names)

        # test for right to left language
        context.set(PTS_IS_RTL, False)
        for name in catalog_names:
            if rtlRegistry.get(name):
                context.set(PTS_IS_RTL, True)
                break

        return [translationRegistry[name] for name in catalog_names]

    security.declarePrivate('setLanguageFallbacks')
    def setLanguageFallbacks(self, fallbacks=None):
        if fallbacks is None:
            fallbacks = LANGUAGE_FALLBACKS
        self._fallbacks = fallbacks


    security.declareProtected(view, 'getLanguageName')
    def getLanguageName(self, code):
        for (ccode, cdomain), cnames in catalogRegistry.items():
            if ccode == code:
                for cname in cnames:
                    cat = self._getOb(cname)
                    if cat.name:
                        return cat.name

    security.declareProtected(view, 'getLanguages')
    def getLanguages(self, domain=None):
        """
        Get available languages
        """
        if domain is None:
            # no domain, so user wants 'em all
            langs = catalogRegistry.keys()
            # uniquify
            d = {}
            for l in langs:
                d[l[0]] = 1
            l = d.keys()
        else:
            l = [k[0] for k in catalogRegistry.keys() if k[1] == domain]
        l.sort()
        return l

    security.declareProtected(view, 'isRTL')
    def isRTL(self, context, domain):
        """get RTL settings
        """
        context = self._getContext(context)
        pts_is_rtl = context.get(PTS_IS_RTL, None)
        if pts_is_rtl is None:
            # call getCatalogsForTranslation to initialize the negotiator
            self.getCatalogsForTranslation(context, domain)
        return context.get(PTS_IS_RTL, False)

    security.declareProtected(view, 'utranslate')
    def utranslate(self, domain, msgid, mapping=None, context=None,
                  target_language=None, default=None):
        """
        translate() using unicode
        """
        return self.translate(domain, msgid, mapping, context,
                  target_language, default, as_unicode=True)

    security.declareProtected(view, 'translate')
    def translate(self, domain, msgid, mapping=None, context=None,
                  target_language=None, default=None, as_unicode=False):
        """
        translate a message using the default encoding
        """
        global global_tracker
        if not msgid:
            # refuse to translate an empty msgid
            return default

        # ZPT passes the object as context.  That's wrong according to spec.
        context = self._getContext(context)

        catalogs = self.getCatalogsForTranslation(context, domain, target_language)
        for catalog in catalogs:
            try:
                text = getMessage(catalog, msgid, default)
            except KeyError:
                # it's not in this catalog, try the next one
                continue
            # found! negotiate output encodings now
            if hasattr(context, 'pt_output_encoding'):
                # OpenPT
                encodings = catalog._info.get('preferred-encodings', '').split()
                if encodings:
                    context.pt_output_encoding.restrict(catalog, encodings)
            elif not as_unicode:
                # ZPT probably
                # ask HTTPResponse to encode it for us
                text = context.RESPONSE._encode_unicode(text)
            break
        else:
            # Did the fallback fail?  Sigh, use the default.
            # OpenTAL provides a default text.
            # TAL doesn't but will use the default
            # if None is returned
            text = default
            if target_language is None:
                target_language = self.negotiate_language(context, domain)
            global_tracker.recordFailure(domain, msgid, target_language)

        # Now we need to do the interpolation
        return self.interpolate(text, mapping)

    security.declarePrivate('negotiate_language')
    def negotiate_language(self, context, domain):
        if context is None:
            raise TypeError, 'No destination language'
        langs = [m[0] for m in catalogRegistry.keys() if m[1] == domain] + \
                [m[0] for m in fbcatalogRegistry.keys() if m[1] == domain]
        for fallback in self._fallbacks:
            if fallback not in langs:
                langs.append(fallback)
        return negotiator.negotiate(langs, context, 'language')

    security.declareProtected(view, 'getDomain')
    def getDomain(self, domain):
        """
        return a domain instance
        """
        return Domain(domain, self)

    security.declarePrivate('interpolate')
    def interpolate(self, text, mapping):
        """
        Insert the data passed from mapping into the text
        """

        # XXX: why this big try/except?
        try:

            # If the mapping does not exist, make a "raw translation" without
            # interpolation.
            if mapping is None or type(text) not in (StringType, UnicodeType):
                # silly wabbit!
                return text

            get = map_get
            try:
                mapping.get('')
            except AttributeError:
                get = getattr

            # Find all the spots we want to substitute
            to_replace = _interp_regex.findall(text)

            # ZPT (string) or OpenPT (unicode)?
            if type(text) is StringType:
                conv = str
            else:
                conv = XML

            # Now substitute with the variables in mapping
            for string in to_replace:
                var = _get_var_regex.findall(string)[0]
                value = get(mapping, var)
                try:
                    value = value()
                except (TypeError, AttributeError):
                    pass
                if value is None:
                    value = string
                if type(value) not in (StringType, UnicodeType):
                    # FIXME: we shouldn't do this. We should instead
                    # return a list. But i'm not sure about how to use
                    # the regex to split the text.
                    value = conv(value)
                text = text.replace(string, value)

            return text

        except:
            log('interpolation error', PROBLEM, error=sys.exc_info())
            return text

    security.declareProtected(view_management_screens, 'manage_main')
    def manage_main(self, REQUEST, *a, **kw):
        """
        Wrap Folder's manage_main to render international characters
        """
        # ugh, API cruft
        if REQUEST is self and a:
            REQUEST = a[0]
            a = a[1:]
        # wrap the special dtml method Folder.manage_main into a valid
        # acquisition context. Required for Zope 2.8+.
        try:
            r = Folder.manage_main(self, self, REQUEST, *a, **kw)
        except AttributeError:
            manage_main = ImplicitAcquisitionWrapper(Folder.manage_main, self)
            r = manage_main(self, self, REQUEST, *a, **kw)
        if type(r) is UnicodeType:
            r = r.encode('utf-8')
        REQUEST.RESPONSE.setHeader('Content-type', 'text/html; charset=utf-8')
        return r

    security.declareProtected(view_management_screens, 'manage_tracker')
    def manage_tracker(self, REQUEST=None):
        """Defers all to the global_tracker
        """
        global global_tracker
        return global_tracker.manage_tracker(self, REQUEST)

    security.declareProtected(view, 'getTracker')
    def getTracker(self):
        """The domain tracker of that PTS (used only for ZMI template)
        """
        global global_tracker
        return global_tracker

InitializeClass(PlacelessTranslationService)
