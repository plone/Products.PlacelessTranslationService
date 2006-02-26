"""File-like objects that read from or write to a string buffer.

This implements (nearly) all stdio methods.

f = StringIO()      # ready for writing
f = StringIO(buf)   # ready for reading
f.close()           # explicitly release resources held
flag = f.isatty()   # always false
buf = f.read()      # returns the whole file (like getvalue())
buf = f.readline()  # returns one line from the list buffer
list = f.readlines()# the whole list buffer
f.write(buf)        # write at current position
f.writelines(list)  # extends the list buffer with another list
f.getvalue()        # return whole file's contents as a string

Notes:

FasterStringIO is a very basic but fast implementation with lot's of limitations.
I ripped of all functionality that isn't needed by TAL and replaced the rest
with a very basic implementation.

Limitations:

 * read() does return all data
 * no seek/truncate/tell methods are available
 * write is unicode aware
 * readlines does't guarantee lines
 * no len value available

You need the global request patch from PlacelessTranslationService!

Based on the StringIO module from python 2.3
Adapted for the PlacelessTranslationService / SpeedPack by Christian Heimes

Thanks to Andreas Jung for his idea to use list.append().
"""

from types import UnicodeType
from TAL.TALInterpreter import _write_ValueError

class FasterStringIO:
    """class FasterStringIO([buffer])

    unicode aware and restricted version of StringIO for Zope's TAL
    """
    def __init__(self, buf = ''):
        self.buf = []
        self.buf.append(buf)
        self.linepos = 0
        self.closed = 0

    def __iter__(self):
        return self

    def next(self):
        if self.closed:
            raise StopIteration
        r = self.readline()
        if not r:
            raise StopIteration
        return r

    def close(self):
        if not self.closed:
            self.closed = 1
            self.write = _write_ValueError
            del self.buf

    def isatty(self):
        if self.closed:
            raise ValueError("I/O operation on closed file")
        return False

    def seek(self, pos, mode = 0):
        raise RuntimeError("FasterStringIO doesn't support seeking")

    def tell(self):
        if self.closed:
            raise RuntimeError("FasterStringIO doesn't support tell")

    def read(self):
        if self.closed:
            raise ValueError("I/O operation on closed file")
        return ''.join(self.buf)

    def readline(self, length=None):
        if self.closed:
            raise ValueError("I/O operation on closed file")
        if self.linepos <= len(self.buf):
            self.linepos+=1
            return self.buf[self.linepos]

    def readlines(self):
        return self.buf

    def truncate(self, size=None):
        raise RuntimeError("FasterStringIO doesn't support truncating")

    def write(self, s):
        if self.closed:
            raise ValueError("I/O operation on closed file")
        if not s: return

        if isinstance(s, UnicodeType):
            # XXX: import the get_request method
            # this will fail the first time we need it if the patch wasn't applied
            # before
            try:
                from Globals import get_request
            except ImportError:
                from PatchStringIO import applyRequestPatch
                applyRequestPatch()
                request = None
            else:
                request = get_request()

            try:
                response = request.RESPONSE
                s = response._encode_unicode(s)
            except AttributeError:
                # not an HTTPResponse
                pass

        self.buf.append(s)

    def writelines(self, list):
        self.buf.extend(list)

    def flush(self):
        if self.closed:
            raise RuntimeError("I/O operation on closed file")

    def getvalue(self):
        return self.read()

__all__ = ["StringIO"]
