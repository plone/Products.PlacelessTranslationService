import ZTUtils, ZPublisher

from messageid import MessageID, MessageIDFactory, translate_msgid_with_engine

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

