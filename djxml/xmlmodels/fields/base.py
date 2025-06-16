import copy
from lxml import etree

from django.core.exceptions import ValidationError

from django.utils.encoding import force_str

from ..descriptors import ImmutableFieldBase
from ..exceptions import XmlSchemaValidationError


class NOT_PROVIDED:
    pass


class XmlField(object):
    # These track each time a Field instance is created. Used to retain order.
    creation_counter = 0

    #: If true, the field is the primary xml element
    is_root_field = False

    #: an instance of lxml.etree.XMLParser, to override the default
    parser = None

    #: Used by immutable descriptors to
    value_initialized = False

    def __init__(self, name=None, required=False, default=NOT_PROVIDED, parser=None):
        self.name = name
        self.required = required
        self.default = default
        self.parser = parser

        # Adjust the appropriate creation counter, and save our local copy.
        self.creation_counter = XmlField.creation_counter
        XmlField.creation_counter += 1

    def __cmp__(self, other):
        # This is needed because bisect does not take a comparison function.
        a, b = self.creation_counter, other.creation_counter
        return (a > b) - (a < b)

    def __lt__(self, other):
        return self.creation_counter < other.creation_counter

    def __deepcopy__(self, memodict):
        # We don't have to deepcopy very much here, since most things are not
        # intended to be altered after initial creation.
        obj = copy.copy(self)
        memodict[id(self)] = obj
        return obj

    def to_python(self, value):
        """
        Converts the input value into the expected Python data type, raising
        django.core.exceptions.ValidationError if the data can't be converted.
        Returns the converted value. Subclasses should override this.
        """
        return value

    def run_validators(self, value):
        pass

    def validate(self, value, model_instance):
        pass

    def clean(self, value, model_instance):
        """
        Convert the value's type and run validation. Validation errors from
        to_python and validate are propagated. The correct value is returned
        if no error is raised.
        """
        value = self.to_python(value)
        self.validate(value, model_instance)
        self.run_validators(value)
        return value

    def set_attributes_from_name(self, name):
        self.name = name
        self.attname = self.get_attname()

    def contribute_to_class(self, cls, name):
        self.set_attributes_from_name(name)
        self.model = cls
        cls._meta.add_field(self)

    def get_attname(self):
        return self.name

    def get_cache_name(self):
        return "_%s_cache" % self.name

    def has_default(self):
        """Returns a boolean of whether this field has a default value."""
        return self.default is not NOT_PROVIDED

    def get_default(self):
        """Returns the default value for this field."""
        if self.has_default():
            if callable(self.default):
                return self.default()
            return force_str(self.default, strings_only=True)
        return None


class XmlElementField(XmlField, metaclass=ImmutableFieldBase):
    def validate(self, value, model_instance):
        if value is None:
            if not self.value_initialized or not self.required:
                return

        if not isinstance(value, etree._Element):
            if hasattr(value, "getroot"):
                try:
                    value = value.getroot()
                except:
                    pass
                else:
                    if isinstance(value, etree._Element):
                        return

            opts = model_instance._meta
            raise ValidationError(
                (
                    "Field %(field_name)r on xml model "
                    "%(app_label)s.%(object_name)s is not an"
                    " instance of lxml.etree._Element"
                )
                % {
                    "field_name": self.name,
                    "app_label": opts.app_label,
                    "object_name": opts.object_name,
                }
            )


class XmlPrimaryElementField(XmlElementField):
    is_root_field = True

    def validate(self, value, model_instance):
        if model_instance._meta.xsd_schema is not None:
            try:
                model_instance._meta.xsd_schema.assertValid(value)
            except Exception as e:
                raise XmlSchemaValidationError(str(e))

    def contribute_to_class(self, cls, name):
        assert not cls._meta.has_root_field, (
            "An xml model can't have more than one XmlPrimaryElementField"
        )
        super().contribute_to_class(cls, name)
        cls._meta.has_root_field = True
        cls._meta.root_field = self
