import re

from lxml import etree

from django.core.exceptions import ValidationError

from django.utils.encoding import force_str

from .base import XmlField
from ..descriptors import XPathFieldBase
from .utils import parse_datetime

__all__ = (
    "XPathField",
    "XPathListField",
    "XPathSingleNodeField",
    "XPathTextField",
    "XPathIntegerField",
    "XPathFloatField",
    "XPathDateTimeField",
    "XPathBooleanField",
    "XPathTextListField",
    "XPathIntegerListField",
    "XPathFloatListField",
    "XPathDateTimeListField",
    "XPathBooleanListField",
    "XPathHtmlField",
    "XPathHtmlListField",
    "XPathInnerHtmlMixin",
    "XPathInnerHtmlField",
    "XPathInnerHtmlListField",
)


class XPathField(XmlField, metaclass=XPathFieldBase):
    """
    Base field for abstracting the retrieval of node results from the xpath
    evaluation of an xml etree.
    """

    #: XPath query string
    xpath_query = None

    #: Dict of extra prefix/uri namespaces pairs to pass to xpath()
    extra_namespaces = {}

    #: Extra extensions to pass on to lxml.etree.XPathEvaluator()
    extensions = {}

    required = True

    def __init__(self, xpath_query, extra_namespaces=None, extensions=None, **kwargs):
        if isinstance(self.__class__, XPathField):
            raise RuntimeError("%r is an abstract field type.")

        self.xpath_query = xpath_query
        if extra_namespaces is not None:
            self.extra_namespaces = extra_namespaces
        if extensions is not None:
            self.extensions = extensions

        super().__init__(**kwargs)

    def validate(self, nodes, model_instance):
        super().validate(nodes, model_instance)
        if nodes is None:
            if not self.value_initialized or not self.required:
                return nodes
        try:
            node_count = len(nodes)
        except TypeError:
            node_count = 1
        if self.required and node_count == 0:
            msg = "XPath query %r did not match any nodes" % self.xpath_query
            raise model_instance.DoesNotExist(msg)

    def clean(self, value, model_instance):
        """
        Run validators on raw value, not the value returned from
        self.to_python(value) (as it is in the parent clean() method)
        """
        self.validate(value, model_instance)
        self.run_validators(value)
        value = self.to_python(value)
        return value

    def get_default(self):
        value = super().get_default()
        if value is None:
            return value
        else:
            return [value]

    def __unicode__(self):
        return "%(field_name)s[%(xpath_query)r]" % {
            "field_name": self.name,
            "xpath_query": self.xpath_query,
        }

    def __repr__(self):
        return "<%(cls)s: %(field)s>" % {
            "cls": self.__class__.__name__,
            "field": self.__unicode__().encode("raw_unicode_escape"),
        }


class XPathListField(XPathField):
    """
    Field which abstracts retrieving a list of nodes from the xpath evaluation
    of an xml etree.
    """

    def to_python(self, value):
        if value is None:
            return value
        if isinstance(value, list):
            return value
        else:
            return list(value)


class XPathSingleNodeField(XPathField):
    """
    Field which abstracts retrieving the first node result from the xpath
    evaluation of an xml etree.
    """

    #: Whether to ignore extra nodes and return the first node if the xpath
    #: evaluates to more than one node.
    #:
    #: To return the full list of nodes, Use XPathListField
    ignore_extra_nodes = False

    def __init__(self, xpath_query, ignore_extra_nodes=False, **kwargs):
        self.ignore_extra_nodes = ignore_extra_nodes
        super().__init__(xpath_query, **kwargs)

    def validate(self, nodes, model_instance):
        super().validate(nodes, model_instance)
        if nodes is None:
            if not self.value_initialized or not self.required:
                return nodes
        if isinstance(nodes, str):
            node_count = 1
        else:
            try:
                node_count = len(nodes)
            except TypeError:
                node_count = 1
        if not self.ignore_extra_nodes and node_count > 1:
            msg = "XPath query %r matched more than one node" % self.xpath_query
            raise model_instance.MultipleObjectsReturned(msg)

    def to_python(self, value):
        if value is None:
            return value
        if isinstance(value, list):
            if len(value) == 0:
                return None
            else:
                return value[0]
        elif isinstance(value, str):
            return value
        else:
            # Possible throw exception here
            return value


class XPathTextField(XPathSingleNodeField):
    #: A tuple of strings which should be interpreted as None.
    none_vals = ()

    def __init__(self, *args, **kwargs):
        none_vals = kwargs.pop("none_vals", None)
        if none_vals is not None:
            self.none_vals = [force_str(v) for v in none_vals]
        super().__init__(*args, **kwargs)

    def validate(self, value, model_instance):
        super().validate(value, model_instance)
        if len(self.none_vals):
            value = self.to_python(value)
            if self.required and value in self.none_vals:
                error_msg = ("%(field)s is required, but value %(value)r is mapped to None") % {
                    "field": str(self),
                    "value": value,
                }
                raise model_instance.DoesNotExist(error_msg)

    def to_python(self, value):
        value = super().to_python(value)
        if value is None:
            return value
        if isinstance(value, etree._Element):
            return force_str(value.text)
        else:
            return force_str(value)


class XPathIntegerField(XPathTextField):
    def to_python(self, value):
        value = super().to_python(value)
        if value is None:
            return value
        else:
            try:
                return int(value)
            except ValueError:
                value = float(value)
                if not value.is_integer():
                    raise
                else:
                    return int(value)


class XPathFloatField(XPathTextField):
    def to_python(self, value):
        value = super().to_python(value)
        if value is None:
            return value
        else:
            return float(value)


class XPathDateTimeField(XPathTextField):
    def to_python(self, value):
        value = super().to_python(value)
        if value is None:
            return value
        else:
            return parse_datetime(value)


class XPathBooleanField(XPathTextField):
    true_vals = ("true",)
    false_vals = ("false",)

    def __init__(self, *args, **kwargs):
        true_vals = kwargs.pop("true_vals", None)
        if true_vals is not None:
            self.true_vals = true_vals
        false_vals = kwargs.pop("false_vals", None)
        if false_vals is not None:
            self.false_vals = false_vals
        super().__init__(*args, **kwargs)

    def validate(self, value, model_instance):
        if value is True or value is False:
            return
        super().validate(value, model_instance)
        if value is None:
            return
        value = XPathTextField.to_python(self, value)
        if value is None:
            return
        if value not in self.true_vals and value not in self.false_vals:
            opts = model_instance._meta
            exc_msg = (
                "%(field)s on xmlmodel %(app_label)s.%(object_name)s "
                "has value %(val)r not in true_vals or false_vals"
                % {
                    "field": repr(self).decode("raw_unicode_escape"),
                    "app_label": opts.app_label,
                    "object_name": opts.object_name,
                    "val": value,
                }
            )
            raise ValidationError(exc_msg)

    def to_python(self, value):
        if value is None or value is True or value is False:
            return value
        value = super().to_python(value)
        if value in self.true_vals:
            return True
        elif value in self.false_vals:
            return False
        else:
            return value


class XPathTextListField(XPathListField):
    def to_python(self, value):
        value = super().to_python(value)
        if value is None:
            return value
        else:
            return [force_str(getattr(v, "text", v)) for v in value]


class XPathIntegerListField(XPathTextListField):
    def to_python(self, value):
        value = super().to_python(value)
        if value is None:
            return value
        else:
            return [int(v) for v in value]


class XPathFloatListField(XPathTextListField):
    def to_python(self, value):
        value = super().to_python(value)
        if value is None:
            return value
        else:
            return [float(v) for v in value]


class XPathDateTimeListField(XPathTextListField):
    def to_python(self, value):
        value = super().to_python(value)
        if value is None:
            return value
        else:
            return [parse_datetime(v) for v in value]


class XPathBooleanListField(XPathTextListField):
    true_vals = ("true",)
    false_vals = ("false",)

    def __init__(self, *args, **kwargs):
        true_vals = kwargs.pop("true_vals", None)
        if true_vals is not None:
            self.true_vals = true_vals
        false_vals = kwargs.pop("false_vals", None)
        if false_vals is not None:
            self.false_vals = false_vals
        super().__init__(*args, **kwargs)

    def validate(self, value, model_instance):
        super().validate(value, model_instance)
        values = super().to_python(value)
        if values is None:
            return
        for value in values:
            if value not in self.true_vals and value not in self.false_vals:
                opts = model_instance._meta
                raise ValidationError(
                    (
                        "XPathBooleanListField %(field)r on "
                        " xml model %(app_label)s.%(object_name)s"
                        " has value %(value)r not in 'true_vals'"
                        " or 'false_vals'"
                    )
                    % {
                        "field": self.name,
                        "app_label": opts.app_label,
                        "object_name": opts.object_name,
                        "value": value,
                    }
                )

    def to_python(self, value):
        value = super().to_python(value)
        if value is None:
            return value
        elif value in self.true_vals:
            return True
        elif value in self.false_vals:
            return False
        else:
            return value


class XPathHtmlField(XPathSingleNodeField):
    """
    Differs from XPathTextField in that it serializes mixed content to a
    unicode string, rather than simply returning the first text node.
    """

    #: Whether to strip the 'xmlns="http://www.w3.org/1999/xhtml"' from
    #: the serialized html strings
    strip_xhtml_ns = True

    def __init__(self, xpath_query, strip_xhtml_ns=True, **kwargs):
        self.strip_xhtml_ns = strip_xhtml_ns
        super().__init__(xpath_query, **kwargs)

    def format_value(self, value):
        formatted = etree.tostring(value, encoding="unicode", method="html")
        if self.strip_xhtml_ns:
            formatted = formatted.replace(' xmlns="http://www.w3.org/1999/xhtml"', "")
        return formatted

    def to_python(self, value):
        value = super().to_python(value)
        if value is None:
            return value
        if isinstance(value, etree._Element):
            return self.format_value(value)


class XPathHtmlListField(XPathListField):
    """
    Differs from XPathHtmlListField in that it serializes mixed content to
    a unicode string, rather than simply returning the first text node for
    each node in the result.
    """

    #: Whether to strip the 'xmlns="http://www.w3.org/1999/xhtml"' from
    #: the serialized html strings
    strip_xhtml_ns = True

    def __init__(self, xpath_query, strip_xhtml_ns=True, **kwargs):
        self.strip_xhtml_ns = strip_xhtml_ns
        super().__init__(xpath_query, **kwargs)

    def format_value(self, value):
        formatted = etree.tostring(value, encoding="unicode", method="html")
        if self.strip_xhtml_ns:
            formatted = formatted.replace(' xmlns="http://www.w3.org/1999/xhtml"', "")
        return formatted

    def to_python(self, value):
        value = super().to_python(value)
        if value is None:
            return value
        else:
            return [self.format_value(v) for v in value]


class XPathInnerHtmlMixin(object):
    self_closing_re = re.compile(
        r"<(area|base(?:font)?|frame|col|br|hr|input|img|link|meta|param)"
        r"([^/>]*?)></\1>"
    )

    def get_inner_html(self, value):
        if not isinstance(value, str):
            return value
        # Strip surrounding tag
        value = re.sub(r"(?s)^<([^>\s]*)(?:[^>]*>|>)(.*)</\1>$", r"\2", value)
        # Replace open-close tags into self-closing where appropriate
        # e.g. "<br></br>" => "<br/>"
        value = self.self_closing_re.sub(r"<\1\2/>", value)
        # Remove leading and trailing whitespace
        value = value.strip()
        return value


class XPathInnerHtmlField(XPathInnerHtmlMixin, XPathHtmlField):
    def to_python(self, value):
        if value is None:
            return value
        value = super().to_python(value)
        return self.get_inner_html(value)


class XPathInnerHtmlListField(XPathInnerHtmlMixin, XPathHtmlListField):
    def to_python(self, value):
        if value is None:
            return value
        value = super().to_python(value)
        return [self.get_inner_html(v) for v in value]
