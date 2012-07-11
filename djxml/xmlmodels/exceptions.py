from django.core.exceptions import ValidationError

class XmlModelException(Exception):
    pass

class XmlSchemaValidationError(ValidationError):
    pass

class XPathException(XmlModelException):
    pass


class XPathDateTimeException(XPathException):
    pass


class ExtensionException(XmlModelException):
    pass


class ExtensionNamespaceException(XmlModelException):
    pass
