##############################################################################
#    Copyright (C) 2001-2005 Lalo Martins <lalo@laranja.org>,
#                  and Contributors

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
__version__ = '''
$Id$
'''.strip()

from zLOG import LOG, INFO, BLATHER, PROBLEM, WARNING
from UserDict import UserDict
from types import UnicodeType
import sys, os

try:
    True
except NameError:
    True=1
    False=0

NOISY_DEBUG = False

class Registry(UserDict):

    def register(self, name, value):
        self[name] = value

def log(msg, severity=INFO, detail='', error=None):
    if not NOISY_DEBUG and severity == BLATHER:
        return
    if type(msg) is UnicodeType:
        msg = msg.encode(sys.getdefaultencoding(), 'replace')
    if type(detail) is UnicodeType:
        detail = detail.encode(sys.getdefaultencoding(), 'replace')
    LOG('PlacelessTranslationService', severity, msg, detail, error)

def make_relative_location(popath):
    # return ("INSTANCE_HOME", stripped po path)
    # when po is located below INSTANCE_HOME
    # and return ("ZOPE_HOME", stripped po path) 
    # when po is located below ZOPE_HOME

    popath = os.path.normpath(popath)
    instance_home = os.path.normpath(INSTANCE_HOME) + os.sep
    zope_home = os.path.normpath(ZOPE_HOME) + os.sep

    if popath.startswith(instance_home):
        return ("INSTANCE_HOME", popath[len(instance_home):])
    elif popath.startswith(zope_home):
        return ("ZOPE_HOME", popath[len(zope_home):])
    else:
        return ("ABSOLUTE", popath)

