class XmlModelException(Exception):
    pass


class XPathException(XmlModelException):
    pass


class XPathDateTimeException(XPathException):
    pass


class ExtensionException(XmlModelException):
    pass


class ExtensionNamespaceException(XmlModelException):
    pass
