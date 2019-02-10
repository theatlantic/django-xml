from __future__ import absolute_import
import six

from .signals import xmlclass_prepared
from .loading import get_xml_model
from .fields import (SchematronField, XmlField, XPathSingleNodeField,
                     XPathSingleNodeField, XPathListField, XsltField,)


RECURSIVE_RELATIONSHIP_CONSTANT = 'self'

pending_lookups = {}


def add_lazy_relation(cls, field, relation, operation):
    """
    Adds a lookup on ``cls`` when a related field is defined using a string,
    i.e.::

        class MyModel(Model):
            children = EmbeddedXPathField("AnotherModel", "child::*")

    This string can be:

        * RECURSIVE_RELATIONSHIP_CONSTANT (i.e. "self") to indicate a recursive
          relation.

        * The name of a model (i.e "AnotherModel") to indicate another model in
          the same app.

        * An app-label and model name (i.e. "someapp.AnotherModel") to indicate
          another model in a different app.

    If the other model hasn't yet been loaded -- almost a given if you're using
    lazy relationships -- then the relation won't be set up until the
    xmlclass_prepared signal fires at the end of model initialization.

    operation is the work that must be performed once the relation can be
    resolved.
    """
    # Check for recursive relations
    if relation == RECURSIVE_RELATIONSHIP_CONSTANT:
        app_label = cls._meta.app_label
        model_name = cls.__name__

    else:
        # Look for an "app.Model" relation
        try:
            app_label, model_name = relation.split(".")
        except ValueError:
            # If we can't split, assume a model in current app
            app_label = cls._meta.app_label
            model_name = relation
        except AttributeError:
            # If it doesn't have a split it's actually a model class
            app_label = relation._meta.app_label
            model_name = relation._meta.object_name

    # Try to look up the related model, and if it's already loaded resolve the
    # string right away. If get_xml_model returns None, it means that the
    # related model isn't loaded yet, so we need to pend the relation until
    # the class is prepared.
    model = get_xml_model(app_label, model_name, False)
    if model:
        operation(field, model, cls)
    else:
        key = (app_label, model_name)
        value = (cls, field, operation)
        pending_lookups.setdefault(key, []).append(value)


def do_pending_lookups(sender, **kwargs):
    """
    Handle any pending relations to the sending model.
    Sent from xmlclass_prepared.
    """
    key = (sender._meta.app_label, sender.__name__)
    for cls, field, operation in pending_lookups.pop(key, []):
        operation(field, sender, cls)


xmlclass_prepared.connect(do_pending_lookups)


class EmbeddedField(XmlField):

    embedded_model = None

    def contribute_to_class(self, cls, name):
        self.set_attributes_from_name(name)
        self.model = cls

        # Set up for lazy initialized embedded models
        if isinstance(self.embedded_model, six.string_types):
            def _resolve_lookup(field, resolved_model, cls):
                field.embedded_model = resolved_model
            add_lazy_relation(cls, self, self.embedded_model, _resolve_lookup)

        cls._meta.add_field(self)


class EmbeddedXPathField(XPathSingleNodeField, EmbeddedField):

    def __init__(self, xml_model, *args, **kwargs):
        self.embedded_model = xml_model
        super(EmbeddedXPathField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        value = super(EmbeddedXPathField, self).to_python(value)
        if value is None:
            return value
        else:
            return self.embedded_model(value)

    def contribute_to_class(self, cls, name):
        EmbeddedField.contribute_to_class(self, cls, name)


class EmbeddedXPathListField(XPathListField, EmbeddedField):

    def __init__(self, xml_model, *args, **kwargs):
        self.embedded_model = xml_model
        super(EmbeddedXPathListField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        value = super(EmbeddedXPathListField, self).to_python(value)
        if value is None:
            return value
        else:
            return [self.embedded_model(v) for v in value]

    def contribute_to_class(self, cls, name):
        EmbeddedField.contribute_to_class(self, cls, name)


class EmbeddedXsltField(XsltField, EmbeddedField):

    def __init__(self, xml_model, *args, **kwargs):
        self.embedded_model = xml_model
        super(EmbeddedXsltField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        value = super(EmbeddedXsltField, self).to_python(value)
        if value is None:
            return value
        else:
            return self.embedded_model(value)

    def contribute_to_class(self, cls, name):
        EmbeddedField.contribute_to_class(self, cls, name)


class EmbeddedSchematronField(SchematronField, EmbeddedField):

    def __init__(self, xml_model, *args, **kwargs):
        self.embedded_model = xml_model
        super(EmbeddedSchematronField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        value = super(EmbeddedSchematronField, self).to_python(value)
        if value is None:
            return value
        else:
            return self.embedded_model(value)

    def contribute_to_class(self, cls, name):
        EmbeddedField.contribute_to_class(self, cls, name)
