"""A simple implementation of a Message Catalog.

$Id$
"""

from gettext import GNUTranslations
import os, sys, types, codecs, traceback, time
import glob
import re
from stat import ST_MTIME

from Acquisition import aq_parent, Implicit
from DateTime import DateTime
from AccessControl import ClassSecurityInfo
from AccessControl.Permissions import view_management_screens
from Globals import InitializeClass
from Globals import INSTANCE_HOME
from Globals import package_home
import Globals
from OFS.Traversable import Traversable
from Persistence import Persistent
from App.Management import Tabs

import logging
from utils import log, make_relative_location, Registry
from msgfmt import Msgfmt

from zope.tales.tales import Context as TALESContextClass
from Products.PageTemplates.PageTemplateFile import PageTemplateFile

def ptFile(id, *filename):
    if type(filename[0]) is types.DictType:
        filename = list(filename)
        filename[0] = package_home(filename[0])
    filename = os.path.join(*filename)
    if not os.path.splitext(filename)[1]:
        filename = filename + '.pt'
    return PageTemplateFile(filename, '', __name__=id)

permission = 'View management screens'

translationRegistry = Registry()
registerTranslation = translationRegistry.register
rtlRegistry = Registry()
registerRTL = rtlRegistry.register

def getMessage(catalog, id, orig_text=None):
    """get message from catalog

    returns the message according to the id 'id' from the catalog 'catalog' or
    raises a KeyError if no translation was found. The return type is always
    unicode
    """
    msg = catalog.gettext(id)
    if msg is id:
        raise KeyError
    if type(msg) is types.StringType:
        msg = unicode(msg, catalog._charset)
    return msg


class BrokenMessageCatalog(Persistent, Implicit, Traversable, Tabs):
    """ broken message catalog """
    meta_type = title = 'Broken Gettext Message Catalog'
    icon='p_/broken'

    isPrincipiaFolderish = 0
    isTopLevelPrincipiaApplicationObject = 0

    security = ClassSecurityInfo()
    security.declareObjectProtected(view_management_screens)

    def __init__(self, id, pofile, error):
        self._pofile = make_relative_location(pofile)
        self.id = id
        self._mod_time = self._getModTime()
        self.error = traceback.format_exception(error[0],error[1],error[2])

    # modified time helper
    def _getModTime(self):
        """
        """
        try:
            mtime = os.stat(self._getPoFile())[ST_MTIME]
        except (IOError, OSError):
            mtime = 0
        return mtime

    def getIdentifier(self):
        """
        """
        return self.id

    def getId(self):
        """
        """
        return self.id

    security.declareProtected(view_management_screens, 'getError')
    def getError(self):
        """
        """
        return self.error

    def _getPoFile(self):
        """get absolute path of the po file as string
        """
        prefix, pofile = self._pofile
        if prefix == 'ZOPE_HOME':
            return os.path.join(ZOPE_HOME, pofile)
        elif prefix == 'INSTANCE_HOME':
            return os.path.join(INSTANCE_HOME, pofile)
        else:
            return os.path.normpath(pofile)

    security.declareProtected(view_management_screens, 'Title')
    def Title(self):
        return self.title

    def get_size(self):
        """Get the size of the underlying file."""
        return os.path.getsize(self._getPoFile())

    def reload(self, REQUEST=None):
        """ Forcibly re-read the file """
        # get pts
        pts = aq_parent(self)
        name = self.getId()
        pofile = self._getPoFile()
        pts._delObject(name)
        try: pts.addCatalog(GettextMessageCatalog(name, pofile))
        except OSError:
            # XXX TODO
            # remove a catalog if it cannot be loaded from the old location
            raise
        except:
            exc=sys.exc_info()
            log('Message Catalog has errors', logging.WARNING, name, exc)
            pts.addCatalog(BrokenMessageCatalog(name, pofile, exc))
        self = pts._getOb(name)
        if hasattr(REQUEST, 'RESPONSE'):
            if not REQUEST.form.has_key('noredir'):
                REQUEST.RESPONSE.redirect(self.absolute_url())

    security.declareProtected(view_management_screens, 'file_exists')
    def file_exists(self):
        try:
            file = open(self._getPoFile(), 'rb')
        except:
            return False
        return True

    def manage_afterAdd(self, item, container): pass
    def manage_beforeDelete(self, item, container): pass
    def manage_afterClone(self, item): pass

    manage_options = (
        {'label':'Info', 'action':''},
        )

    index_html = ptFile('index_html', globals(), 'www', 'catalog_broken')

InitializeClass(BrokenMessageCatalog)

class GettextMessageCatalog(Persistent, Implicit, Traversable, Tabs):
    """
    Message catalog that wraps a .po file in the filesystem and stores
    the compiled po file in the zodb
    """
    meta_type = title = 'Gettext Message Catalog'
    icon = 'misc_/PlacelessTranslationService/GettextMessageCatalog.png'

    isPrincipiaFolderish = 0
    isTopLevelPrincipiaApplicationObject = 0

    security = ClassSecurityInfo()
    security.declareObjectProtected(view_management_screens)

    def __init__(self, id, pofile, language=None, domain=None):
        """Initialize the message catalog"""
        self._pofile   = make_relative_location(pofile)
        self.id        = id
        self._mod_time = self._getModTime()
        self._language = language
        self._domain   = domain
        self._prepareTranslations(0)

    def _prepareTranslations(self, catch=1):
        """Try to generate the translation object
           if fails remove us from registry
        """
        try: self._doPrepareTranslations()
        except:
            if self.getId() in translationRegistry.keys():
                del translationRegistry[self.getId()]
            if not catch: raise
            else: pass

    def _doPrepareTranslations(self):
        """Generate the translation object from a po file
        """
        self._updateFromFS()
        tro = None
        if getattr(self, '_v_tro', None) is None:
            self._v_tro = tro = translationRegistry.get(self.getId(), None)
        if tro is None:
            moFile = self._getMoFile()
            tro = GNUTranslations(moFile)
            if not self._language:
                self._language = (tro._info.get('language-code', None) # new way
                               or tro._info.get('language', None)) # old way
            if not self._domain:
                self._domain = tro._info.get('domain', None)
            if self._language is None or self._domain is None:
                raise ValueError, 'potfile %s has no metadata, PTS needs a language and a message domain!' % os.path.join(*self._pofile)
            self._language = self._language.lower().replace('_', '-')
            self._other_languages = tro._info.get('x-is-fallback-for', '').split()
            self.preferred_encodings = tro._info.get('preferred-encodings', '').split()
            self.name = unicode(tro._info.get('language-name', ''), tro._charset)
            self.default_zope_data_encoding = tro._charset

            translationRegistry[self.getId()] = self._v_tro = tro

            # right to left support
            is_rtl = tro._info.get('x-is-rtl', 'no').strip().lower()
            if is_rtl in ('yes', 'y', 'true', '1'):
                self._is_rtl = True
            elif is_rtl in ('no', 'n', 'false', '0'):
                self._is_rtl = False
            else:
                raise ValueError, 'Unsupported value for X-Is-RTL' % is_rtl
            rtlRegistry[self.getId()] = self.isRTL()

            missingFileName = self._getPoFile()[:-3] + '.missing'
            if os.access(missingFileName, os.W_OK):
                tro.add_fallback(MissingIds(missingFileName, self._v_tro._charset))
            if self.name:
                self.title = '%s language (%s) for %s' % (self._language, self.name, self._domain)
            else:
                self.title = '%s language for %s' % (self._language, self._domain)

    def filtered_manage_options(self, REQUEST=None):
        return self.manage_options

    def reload(self, REQUEST=None):
        """Forcibly re-read the file
        """
        if self.getId() in translationRegistry.keys():
            del translationRegistry[self.getId()]
        if hasattr(self, '_v_tro'):
            del self._v_tro
        name = self.getId()
        pts = aq_parent(self)
        pofile=self._getPoFile()
        try:
            self._prepareTranslations(0)
            log('reloading %s: %s' % (name, self.title), severity=logging.DEBUG)
        except:
            pts._delObject(name)
            exc=sys.exc_info()
            log('Message Catalog has errors', logging.WARNING, name, exc)
            pts.addCatalog(BrokenMessageCatalog(name, pofile, exc))
        self = pts._getOb(name)
        if hasattr(REQUEST, 'RESPONSE'):
            if not REQUEST.form.has_key('noredir'):
                REQUEST.RESPONSE.redirect(self.absolute_url())

    security.declarePublic('queryMessage')
    def queryMessage(self, id, default=None):
        """Queries the catalog for a message

        If the message wasn't found the default value or the id is returned.
        """
        try:
            return getMessage(translationRegistry[self.getId()],id,default)
        except KeyError:
            if default is None:
                default = id
            return default

    def getLanguage(self):
        """
        """
        return self._language

    def getLanguageName(self):
        """
        """
        return self.name or self._language

    def getOtherLanguages(self):
        """
        """
        return self._other_languages

    def getDomain(self):
        """
        """
        return self._domain

    def getIdentifier(self):
        """
        """
        return self.id

    def getId(self):
        """
        """
        return self.id

    def getInfo(self, name):
        """
        """
        self._prepareTranslations()
        return self._v_tro._info.get(name, None)
    
    def isRTL(self):
        """
        """
        return self._is_rtl

    security.declareProtected(view_management_screens, 'Title')
    def Title(self):
        return self.title

    def _getMoFile(self):
        """get compiled version of the po file as file object
        """
        useCache = True
        if useCache:
            hit, mof = cachedPoFile(self)
            return mof
        else:
            mo = Msgfmt(self._readFile(), self.getId())
            return mo.getAsFile()

    def _getPoFile(self):
        """get absolute path of the po file as string
        """
        prefix, pofile = self._pofile
        if prefix == 'ZOPE_HOME':
            return os.path.join(ZOPE_HOME, pofile)
        elif prefix == 'INSTANCE_HOME':
            return os.path.join(INSTANCE_HOME, pofile)
        else:
            return os.path.normpath(pofile)

    def _readFile(self, reparse=False):
        """Read the data from the filesystem.

        """
        file = open(self._getPoFile(), 'rb')
        data = []
        try:
            # XXX need more checks here
            data = file.readlines()
        finally:
            file.close()
        return data

    def _updateFromFS(self):
        """Refresh our contents from the filesystem

        if the file is newer and we are running in debug mode.
        """
        if Globals.DevelopmentMode:
            mtime = self._getModTime()
            if mtime != self._mod_time:
                self._mod_time = mtime
                self.reload()

    def _getModTime(self):
        """
        """
        try:
            mtime = os.stat(self._getPoFile())[ST_MTIME]
        except (IOError, OSError):
            mtime = 0
        return mtime

    def get_size(self):
        """Get the size of the underlying file."""
        return os.path.getsize(self._getPoFile())

    def getModTime(self):
        """Return the last_modified date of the file we represent.

        Returns a DateTime instance.
        """
        self._updateFromFS()
        return DateTime(self._mod_time)

    def getObjectFSPath(self):
        """Return the path of the file we represent"""
        return self._getPoFile()

    # Zope/OFS integration

    def manage_afterAdd(self, item, container): pass
    def manage_beforeDelete(self, item, container): pass
    def manage_afterClone(self, item): pass

    manage_options = (
        {'label':'Info', 'action':''},
        {'label':'Test', 'action':'zmi_test'},
        )

    index_html = ptFile('index_html', globals(), 'www', 'catalog_info')
    zmi_test = ptFile('zmi_test', globals(), 'www', 'catalog_test')

    security.declareProtected(view_management_screens, 'file_exists')
    def file_exists(self):
        try:
            file = open(self._getPoFile(), 'rb')
        except:
            return False
        return True

    security.declareProtected(view_management_screens, 'getEncoding')
    def getEncoding(self):
        try:
            content_type = self.getHeader('content-type')
            enc = content_type.split(';')[1].strip()
            enc = enc.split('=')[1]
        except: enc='utf-8'
        return enc

    def getHeader(self, header):
        self._prepareTranslations()
        info = self._v_tro._info
        return info.get(header)

    security.declareProtected(view_management_screens, 'displayInfo')
    def displayInfo(self):
        self._prepareTranslations()
        try: info = self._v_tro._info
        except:
            # broken catalog probably
            info={}
        keys = info.keys()
        keys.sort()
        return [{'name': k, 'value': info[k]} for k in keys] + [
            {'name': 'full path', 'value': os.path.join(*self._pofile)},
            {'name': 'last modification', 'value': self.getModTime().ISO()}
            ]

InitializeClass(GettextMessageCatalog)

# template to use to write missing entries to .missing
missing_template = u'''
#. Added on %(date)s
#.
#: %(reference)s%(context)s
#.
#. Orginal text:%(original)s
msgid "%(id)s"
msgstr ""
'''

class MissingIds(Persistent):
    """This behaves like a gettext message catalog but always
    raises a KeyError. However, along the way, it adds the msgid that
    was missing to the .missing file in .po format.
    """

    security = ClassSecurityInfo()
    security.declareObjectProtected(view_management_screens)

    def __init__(self, fileName, charset):
        self._fileName = fileName
        self._charset = charset
        self._ids = {}
        self._pattern = re.compile('msgid "(.*)"$')
        self.parseFile()
        self._v_file = None

    def parseFile(self):
        file = codecs.open(self._fileName, 'r', self._charset)
        for line in file.xreadlines():
            match = self._pattern.search(line)
            if match:
                msgid = match.group(1)
                self._ids[msgid] = 1
        file.close()

    def gettext(self, msgid):
        if not self._ids.has_key(msgid):
            if getattr(self, '_v_file', None) is None:
                self._v_file = codecs.open(self._fileName, 'a', self._charset)
            context_info = None

            # raise an exception so we can get a stack frame
            try:
                raise ZeroDivisionError
            except ZeroDivisionError:
                f = sys.exc_info()[2].tb_frame.f_back
                # gm_f is the frame in which the getMessage in this
                # file executes. 
                gm_f = f.f_back

            # The next line provides a way to detect recursion.
            __exception_formatter__ = 1
            
            # go hunting for the context that called up
            while f is not None:
                locals = f.f_locals
                if locals.get('__exception_formatter__'):
                    # Stop recursion.
                    context_info = ('Recursion Error while trying to find Context',)
                    break
                Context = locals.get('self')
                if isinstance(Context,TALESContextClass):
                    context_info = (
                        Context.source_file,
                        'Line %i, Column %i' % (
                                   Context.position[0],
                                   Context.position[1],
                                   )
                        )
                    original = f.f_back.f_locals.get('default')
                    break
                f = f.f_back

            if context_info is None:
                # lets insert details of the thing that called PTS
                # you can indicate a thing to use instead of PTS
                # by putting:
                #
                # __pts_caller_backcount__ = 1
                #
                # ...in the thing.
                # This is handy, for example, if you have a generic
                # external method or python script that does
                # translations and you want to record what is calling
                # it, and  not just the thing itself.
                #
                # The value is the number of stack frames to count
                # back to find the caller.
                # For external methods, this should be 2
                # For python scripts, it might be 1
                # XXX please add to and correct as appropriate

                # build an inverse list of frames
                frames = []
                f = gm_f
                while 1:
                    frames.append(f)
                    f = f.f_back
                    if f is None:
                        break
                frames.reverse()
                
                caller_f = None
                # look for __pts_caller_backcount__
                for f in frames:
                    backcount = f.f_locals.get('__pts_caller_backcount__')
                    if backcount is not None:
                        while backcount:
                            f = f.f_back
                            backcount -= 1
                        caller_f = f
                        break

                # delete frames list reference to (hopefuly) stop
                # memory leaks
                frames = None

                # report context info as appropriate
                if caller_f is None:
                    context_info = ('No context information could be found',)
                else:                    
                    caller_co = caller_f.f_code
                    context_info = (
                        caller_co.co_filename,
                        'Line %i, in %s' % (caller_f.f_lineno, caller_co.co_name),
                        )

            # insert default text, also probably pretty fragile ;-)
            default = gm_f.f_locals['orig_text']
            if default is None:
                '< No original text supplied >'

            self._v_file.write(missing_template % {
                'id':msgid.replace('"', r'\"'),
                'date':time.asctime(),
                'reference':context_info[0],
                'context':''.join(['\n#. '+line for line in context_info[1:]]),
                'original':''.join(['\n#. '+line for line in default.split('\n')])
                })
            self._v_file.flush()
            self._ids[msgid]=1
        raise KeyError, msgid

InitializeClass(MissingIds)

class MoFileCache(object):
    """Cache for mo files
    """
    
    def __init__(self, path):
        if not os.path.isdir(path):
            try:
                os.makedirs(path)
            except (IOError, OSError):
                path = None
                log("No permission to create directory %s" % path, logging.INFO)
        self._path = path
        
    def storeMoFile(self, catalog):
        """compile and save to mo file for catalog to disk
        
        return value: mo file as file handler
        """
        f = self.getPath(catalog)
        mof = self.compilePo(catalog)
        moExists = os.path.exists(f)
        if (not moExists and os.access(self._path, os.W_OK)) \
          or (moExists and os.access(f, os.W_OK)):
            fd = open(f, 'wb')
            fd.write(mof.read()) # XXX efficient?
            fd.close()
        else:
            log("No permission to write file %s" % f, logging.INFO)
        mof.seek(0)
        return mof
        
    def retrieveMoFile(self, catalog):
        """Load a mo file file for a catalog from disk
        """
        f = self.getPath(catalog)
        if os.path.isfile(f):
            if os.access(f, os.R_OK):
                return open(f, 'rb')
            else:
                log("No permission to read file %s" % f, logging.INFO)
                return None
        
    def getPath(self, catalog):
        """Get the mo file path (cache path + file name)
        """
        id = catalog.getId()
        if id.endswith('.po'):
            id = id[:-3]
        return os.path.join(self._path, '%s.mo' % id)
        
    def isCacheHit(self, catalog):
        """Cache hit?
        
        True: file exists and mod time is newer than mod time of the catalog
        False: file exists but mod time is older
        None: file doesn't exist
        """
        f = self.getPath(catalog)
        ca_mtime = catalog._getModTime()
        try:
            mo_mtime = os.stat(f)[ST_MTIME]
        except (IOError, OSError):
            mo_mtime = 0
        
        if mo_mtime == 0:
            return None
        elif ca_mtime == 0:
            return None
        elif mo_mtime > ca_mtime:
            return True
        else:
            return False
        
    def compilePo(self, catalog):
        """compile a po file to mo
        
        returns a file handler
        """
        mo = Msgfmt(catalog._readFile(), catalog.getId())
        return mo.getAsFile()
        
    def cachedPoFile(self, catalog):
        """Cache a po file (public api)
        
        Returns a file handler on a mo file
        """
        path = self._path
        if path is None:
            return None, self.compilePo(catalog)
        hit = self.isCacheHit(catalog)
        if hit:
            mof = self.retrieveMoFile(catalog)
            if mof is None:
                mof = self.compilePo(catalog)
        else:
            mof = self.storeMoFile(catalog)
        return hit, mof
        
    def purgeCache(self):
        """Purge the cache and remove all compiled mo files
        """
        log("Purging mo file cache", logging.INFO)
        if not os.access(self._path, os.W_OK):
            log("No write permission on folder %s" % self._path, logging.INFO)
            return False
        pattern = os.path.join(self._path, '*.mo')
        for mo in glob.glob(pattern):
            if not os.access(mo, os.W_OK):
                log("No write permission on file %s" % mo, logging.INFO)
                continue
            try:
                os.unlink(mo)
            except IOError:
                log("Failed to unlink %s" % mo, logging.INFO)

_moCache = MoFileCache(os.path.join(INSTANCE_HOME, 'var', 'pts'))
cachedPoFile = _moCache.cachedPoFile
purgeMoFileCache = _moCache.purgeCache

