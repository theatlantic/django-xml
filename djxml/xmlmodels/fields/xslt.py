from lxml import etree, isoschematron

from django.core.exceptions import ValidationError

from .base import XmlField
from ..descriptors import XsltFieldBase


__all__ = ("XsltField", "SchematronField")


class XsltField(XmlField, metaclass=XsltFieldBase):
    #: Instance of lxml.etree.XMLParser
    parser = None

    #: Extra extensions to pass on to lxml.etree.XSLT()
    extensions = {}

    xslt_file = None
    xslt_string = None

    _xslt_tree = None

    def __init__(self, xslt_file=None, xslt_string=None, parser=None, extensions=None, **kwargs):
        super().__init__(**kwargs)

        if xslt_file is None and xslt_string is None:
            raise ValidationError("XsltField requires either xslt_file or xslt_string")
        elif xslt_file is not None and xslt_string is not None:
            raise ValidationError(
                "XsltField.__init__() accepts either "
                "xslt_file or xslt_string as keyword "
                "arguments, not both"
            )

        self.xslt_file = xslt_file
        self.xslt_string = xslt_string
        self.parser = parser
        if extensions is not None:
            self.extensions = extensions

    def get_xslt_tree(self, model_instance):
        if self._xslt_tree is None:
            parser = self.parser
            if parser is None:
                parser = model_instance._meta.get_parser()
            if self.xslt_file is not None:
                self._xslt_tree = etree.parse(self.xslt_file, parser)
            elif self.xslt_string is not None:
                self._xslt_tree = etree.XML(self.xslt_string, parser)
        return self._xslt_tree


class SchematronField(XmlField, metaclass=XsltFieldBase):
    #: Instance of lxml.etree.XMLParser
    parser = None

    #: Extra extensions to pass on to lxml.etree.XSLT()
    extensions = {}

    schematron_file = None
    schematron_string = None

    _schematron = None
    _schematron_tree = None
    _schematron_xslt = None

    def __init__(
        self, schematron_file=None, schematron_string=None, parser=None, extensions=None, **kwargs
    ):
        self.schematron_kwargs = {
            "compile_params": kwargs.pop("compile_params", None),
            "include_params": kwargs.pop("include_params", None),
            "expand_params": kwargs.pop("expand_params", None),
            "phase": kwargs.pop("phase", None),
            "store_xslt": True,
            "store_report": True,
            "store_schematron": True,
        }
        self.schematron_kwargs = {k: v for k, v in self.schematron_kwargs.items() if v is not None}

        super().__init__(**kwargs)

        if schematron_file is None and schematron_string is None:
            raise ValidationError(
                "SchematronField requires either schematron_file or schematron_string"
            )
        elif schematron_file is not None and schematron_string is not None:
            raise ValidationError(
                "SchematronField.__init__() accepts either "
                "schematron_file or schematron_string as "
                "keyword arguments, not both"
            )

        self.schematron_file = schematron_file
        self.schematron_string = schematron_string
        self.parser = parser
        if extensions is not None:
            self.extensions = extensions

    def get_xslt_tree(self, model_instance):
        if self._schematron_xslt is None:
            schematron_tree = self.get_schematron_tree(model_instance)
            self._schematron = isoschematron.Schematron(schematron_tree, **self.schematron_kwargs)
            self._schematron_xslt = self._schematron.validator_xslt.getroot()
        return self._schematron_xslt

    def get_schematron_tree(self, model_instance):
        if self._schematron_tree is None:
            parser = self.parser
            if parser is None:
                parser = model_instance._meta.get_parser()
            if self.schematron_file is not None:
                self._schematron_tree = etree.parse(self.schematron_file, parser)
            elif self.schematron_string is not None:
                self._schematron_tree = etree.XML(self.schematron_string, parser)
        return self._schematron_tree
