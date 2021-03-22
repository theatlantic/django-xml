from django.core.exceptions import ValidationError

class XmlModelException(Exception):
    pass

class XmlSchemaValidationError(XmlModelException):
    pass

class XPathException(XmlModelException):
    pass

class XsltException(XmlModelException):

    def __init__(self, apply_exception, xslt_func):
        self.apply_exception = apply_exception
        self.error_log = xslt_func.error_log

    def __str__(self):
        return str(self.apply_exception)

    def __unicode__(self):
        msg = str(self.apply_exception)
        debug_output = self.get_debug_output()
        if len(debug_output) > 0:
            msg += "\n\n" + debug_output
        return msg

    def get_debug_output(self):
        debug_lines = []
        for entry in self.error_log:
            entry_filename = '%s ' % entry.filename if entry.filename != '<string>' else ''
            debug_line = '%(msg)s [%(file)sline %(line)s, col %(col)s]' % {
                'file': entry_filename,
                'line': entry.line,
                'col': entry.column,
                'msg': entry.message,
            }
            debug_lines.append(debug_line)
        return u"\n".join(debug_lines)

class XPathDateTimeException(XPathException):
    pass


class ExtensionException(XmlModelException):
    pass


class ExtensionNamespaceException(XmlModelException):
    pass
