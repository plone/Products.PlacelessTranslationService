import ZTUtils, ZPublisher

from TAL.TALInterpreter import TALInterpreter
from TAL.TALInterpreter import BOOLEAN_HTML_ATTRS
from TAL.TALInterpreter import escape

from TAL.TALDefs import attrEscape

from Products.PlacelessTranslationService.PlacelessTranslationService \
    import PTSWrapper 

from messageid import MessageID, MessageIDFactory

def new_do_i18nVariable(self, stuff):
    varname, program, expression = stuff
    if expression is None:
        # The value is implicitly the contents of this tag, so we have to
        # evaluate the mini-program to get the value of the variable.
        state = self.saveState()
        try:
            tmpstream = self.StringIO()
            self.interpretWithStream(program, tmpstream)
            value = normalize(tmpstream.getvalue())
        finally:
            self.restoreState(state)
    else:
        # Evaluate the value to be associated with the variable in the
        # i18n interpolation dictionary.
        value = self.engine.evaluate(expression)
        # added by patch
        if isinstance(value, MessageID):
            # Translate this now.
            value = self.engine.translate(value.domain, value)
        # added by patch
    # Either the i18n:name tag is nested inside an i18n:translate in which
    # case the last item on the stack has the i18n dictionary and string
    # representation, or the i18n:name and i18n:translate attributes are
    # in the same tag, in which case the i18nStack will be empty.  In that
    # case we can just output the ${name} to the stream
    i18ndict, srepr = self.i18nStack[-1]
    i18ndict[varname] = value
    placeholder = '${%s}' % varname
    srepr.append(placeholder)
    self._stream_write(placeholder)
 

def new_do_insertText_tal(self, stuff):
    text = self.engine.evaluateText(stuff[0])
    if text is None:
        return
    if text is self.Default:
        self.interpret(stuff[1])
        return
    # added by patch
    if isinstance(text, MessageID):
        # Translate this now.
        text = self.engine.translate(text.domain, text)
    # added by patch
    s = escape(text)
    self._stream_write(s)
    i = s.rfind('\n')
    if i < 0:
        self.col = self.col + len(s)
    else:
        self.col = len(s) - (i + 1)

def new_attrAction_tal(self, item):
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
        #import pdb; pdb.set_trace()
        if isinstance(value, MessageID):
            # Translate this now.
            value = self.engine.translate(value.domain, value)
        
        if xlat:
            translated = self.translate(msgid or value, value, {})
            if translated is not None:
                value = translated
        if value is None:
            value = name
        elif evalue is self.Default:
            value = attrEscape(value)
        else:
            value = escape(value, quote=1)
        value = '%s="%s"' % (name, value)
    return ok, name, value
    


TALInterpreter.do_insertText_tal = new_do_insertText_tal
TALInterpreter.bytecode_handlers_tal["insertText"] = new_do_insertText_tal
TALInterpreter.do_i18nVariable = new_do_i18nVariable
TALInterpreter.bytecode_handlers['i18nVariable'] = new_do_i18nVariable
print 'b'
TALInterpreter.attrAction_tal = new_attrAction_tal
TALInterpreter.bytecode_handlers_tal["<attrAction>"] = new_attrAction_tal

print 'a'



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


old_complex_marshal = ZTUtils.Zope.complex_marshal
def new_complex_marshal(pairs):
    i = len(pairs)
    while i > 0:
        i = i - 1
        name, value = pairs[i]
        if type(value) is MessageID:
            pairs[i] = ('%s@id@i18n' % name, value)
            pairs.append(('%s@domain@i18n' % name, value.domain))
            pairs.append(('%s@mapping@i18n' % name, value.mapping))
            pairs.append(('%s@default@i18n' % name, value.default))
    return old_complex_marshal(pairs)

ZTUtils.Zope.complex_marshal = new_complex_marshal


old_processInputs = ZPublisher.HTTPRequest.HTTPRequest.processInputs
def new_processInputs(self, *args, **kw):
    old_processInputs(self, *args, **kw)
    d = {}
    for key, value in self.form.items():
        if key.endswith('@i18n'):
            l = key.split('@')
            id = '@'.join(l[:-2])
            msg = d.setdefault(id, {})
            msg[l[-2]] = value
            del self.form[key]
    for key, value in d.items():
        id = value['id']
        domain = value['domain']
        default = value['default']
        msg=MessageID(id, domain, default)
        msg.mapping.update(dict(value.get('mapping', {})))
        self.form[key] = msg

ZPublisher.HTTPRequest.HTTPRequest.processInputs = new_processInputs
