##############################################################################
#    Copyright (C) 2001, 2002, 2003 Lalo Martins <lalo@laranja.org>,
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
"""A simple implementation of a Message Catalog.

$Id: GettextMessageCatalog.py,v 1.25 2004/07/18 18:33:07 tiran Exp $
"""

from gettext import GNUTranslations
import os, sys, types, codecs, traceback, time
import re

from Acquisition import aq_parent, Implicit
from DateTime import DateTime
from AccessControl import ClassSecurityInfo
from AccessControl.Permissions import view, view_management_screens
from Globals import InitializeClass
import Globals
from OFS.Traversable import Traversable
from Persistence import Persistent, Overridable
from App.Management import Tabs
from OFS.Uninstalled import BrokenClass

from utils import log, Registry, INFO, BLATHER, PROBLEM
from msgfmt import Msgfmt

try:
    from Products.PageTemplates.TALES import Context as TALESContextClass
except ImportError:
    # must be using OpenTAL
    TALESContextClass = None

try:
    True
except NameError:
    True=1
    False=0

try:
    from Products.OpenPT.OpenPTFile import OpenPTFile as ptFile
except ImportError:
    from Products.PageTemplates.PageTemplateFile import PageTemplateFile
    from Globals import package_home
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
        self._pofile = pofile
        #self.id = os.path.split(self._pofile)[-1]
        self.id = id
        self._mod_time = self._getModTime()
        self.error = traceback.format_exception(error[0],error[1],error[2])

    # modified time helper
    def _getModTime(self):
        """
        """
        try:
            mtime = os.stat(self._pofile)[8]
        except IOError:
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

    security.declareProtected(view_management_screens, 'Title')
    def Title(self):
        return self.title

    def get_size(self):
        """Get the size of the underlying file."""
        return os.path.getsize(self._pofile)

    def reload(self, REQUEST=None):
        """ Forcibly re-read the file """
        # get pts
        pts = aq_parent(self)
        name = self.getId()
        pofile = self._pofile
        pts._delObject(name)
        try: pts.addCatalog(GettextMessageCatalog(name, pofile))
        except OSError:
            # XXX TODO
            # remove a catalog if it cannot be loaded from the old location
            raise
        except:
            exc=sys.exc_info()
            log('Message Catalog has errors', PROBLEM, name, exc)
            pts.addCatalog(BrokenMessageCatalog(name, pofile, exc))
        self = pts._getOb(name)
        if hasattr(REQUEST, 'RESPONSE'):
            if not REQUEST.form.has_key('noredir'):
                REQUEST.RESPONSE.redirect(self.absolute_url())

    security.declareProtected(view_management_screens, 'file_exists')
    def file_exists(self):
        try:
            file = open(self._pofile, 'rb')
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
        self._pofile   = pofile
        #self.id        = os.path.split(self._pofile)[-1]
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
                raise ValueError, 'potfile has no metadata, PTS needs a language and a message domain!'
            self._language = self._language.lower().replace('_', '-')
            self._other_languages = tro._info.get('x-is-fallback-for', '').split()
            self.preferred_encodings = tro._info.get('preferred-encodings', '').split()
            self.name = unicode(tro._info.get('language-name', ''), tro._charset)
            self.default_zope_data_encoding = tro._charset
            translationRegistry[self.getId()] = self._v_tro = tro
            missingFileName = self._pofile[:-3] + '.missing'
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
        pofile=self._pofile
        try:
            self._prepareTranslations(0)
            log('reloading %s: %s' % (name, self.title), severity=BLATHER)
        except:
            pts._delObject(name)
            exc=sys.exc_info()
            log('Message Catalog has errors', PROBLEM, name, exc)
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

    security.declareProtected(view_management_screens, 'Title')
    def Title(self):
        return self.title

    def _getMoFile(self):
        """get compiled version of the po file as file object
        """
        mo = Msgfmt(self._readFile(), self.getId())
        return mo.getAsFile()

    def _readFile(self, reparse=False):
        """Read the data from the filesystem.

        """
        file = open(self._pofile, 'rb')
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
            mtime = os.stat(self._pofile)[8]
        except IOError:
            mtime = 0
        return mtime

    def get_size(self):
        """Get the size of the underlying file."""
        return os.path.getsize(self._pofile)

    def getModTime(self):
        """Return the last_modified date of the file we represent.

        Returns a DateTime instance.
        """
        self._updateFromFS()
        return DateTime(self._mod_time)

    def getObjectFSPath(self):
        """Return the path of the file we represent"""
        return self._pofile

    ############################################################
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
            file = open(self._pofile, 'rb')
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
            {'name': 'full path', 'value': self._pofile},
            {'name': 'last modification', 'value': self.getModTime().ISO()}
            ]
    #
    ############################################################

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
            
            if TALESContextClass:
                # with ZPT TALES, we can provide some context as to
                # where this message was found
                
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
