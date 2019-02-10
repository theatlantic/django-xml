from __future__ import absolute_import
import six
import functools

from lxml import etree

from .exceptions import XsltException


class Creator(object):
    """
    A placeholder class that provides a way to set the attribute on the model.
    """
    def __init__(self, field):
        self.field = field

    def __get__(self, model_instance, type=None):
        return model_instance.__dict__[self.field.name]

    def __set__(self, model_instance, value):
        cleaned_value = self.field.clean(value, model_instance)
        model_instance.__dict__[self.field.name] = cleaned_value
        if value is not None:
            model_instance.__dict__[self.cache_name] = cleaned_value


class ImmutableCreator(Creator):

    def __init__(self, field):
        super(ImmutableCreator, self).__init__(field)
        self.field.value_initialized = False
        self.cache_name = field.get_cache_name()

    def __set__(self, model_instance, value):
        if '_field_inits' not in model_instance.__dict__:
            model_instance._field_inits = {}
        if model_instance._field_inits.get(self.field.name, False):
            raise TypeError("%s.%s is immutable" \
                % (model_instance.__class__.__name__, self.field.name))

        super(ImmutableCreator, self).__set__(model_instance, value)

        if model_instance.__dict__[self.field.name] is not None:
            model_instance._field_inits[self.field.name] = True
            self.field.value_initialized = True


class FieldBase(type):
    """
    A metaclass for custom Field subclasses. This ensures the model's attribute
    has the descriptor protocol attached to it.
    """
    def __new__(cls, name, bases, attrs, **kwargs):
        new_class = super(FieldBase, cls).__new__(cls, name, bases, attrs)

        descriptor_cls_attr = getattr(cls, 'descriptor_cls', None)
        if descriptor_cls_attr is not None:
            kwargs['descriptor_cls'] = descriptor_cls_attr

        new_class.contribute_to_class = make_contrib(
            new_class, attrs.get('contribute_to_class'), **kwargs)
        return new_class


class ImmutableFieldBase(FieldBase):

    descriptor_cls = ImmutableCreator


class XPathObjectDescriptor(ImmutableCreator):

    def __init__(self, field):
        super(XPathObjectDescriptor, self).__init__(field)

    def __get__(self, instance, instance_type=None):
        if instance is None:
            raise AttributeError('Can only be accessed via an instance.')
        try:
            return getattr(instance, self.cache_name)
        except AttributeError:
            tree = instance._get_etree_val()
            query = self.field.xpath_query

            namespaces = {}
            namespaces.update(getattr(instance._meta, 'namespaces', {}))
            namespaces.update(getattr(self.field, 'extra_namespaces', {}))

            extensions = {}
            for k, method in six.iteritems(instance._meta.extensions):
                extensions[k] = functools.partial(method, instance)
            extensions.update(self.field.extensions)

            xpath_eval = etree.XPathEvaluator(tree, namespaces=namespaces,
                extensions=extensions)

            nodes = xpath_eval(query)
            nodes = self.field.clean(nodes, instance)
            setattr(instance, self.cache_name, nodes)
            return nodes


class XPathFieldBase(FieldBase):

    descriptor_cls = XPathObjectDescriptor


class XsltObjectDescriptor(ImmutableCreator):

    def __init__(self, field):
        self.cache_name = field.get_cache_name()
        super(XsltObjectDescriptor, self).__init__(field)

    def __get__(self, instance, instance_type=None):
        if instance is None:
            raise AttributeError('Can only be accessed via an instance.')
        try:
            return getattr(instance, self.cache_name)
        except AttributeError:
            tree = instance._get_etree_val()
            xslt_tree = self.field.get_xslt_tree(instance)

            extensions = {}
            for k, method in six.iteritems(instance._meta.extensions):
                extensions[k] = functools.partial(method, instance)
            extensions.update(self.field.extensions)

            transform = etree.XSLT(xslt_tree, extensions=extensions)
            def xslt_wrapper(xslt_func):
                def wrapper(*args, **kwargs):
                    try:
                        xslt_result = xslt_func(tree, *args, **kwargs)
                    except etree.XSLTApplyError as e:
                        # Put this in frame locals for debugging
                        xslt_source = etree.tostring(xslt_tree, encoding='utf8')
                        raise XsltException(e, xslt_func)
                    return self.field.clean(xslt_result, instance)
                return wrapper
            return xslt_wrapper(transform)


class XsltFieldBase(FieldBase):

    descriptor_cls = XsltObjectDescriptor


def make_contrib(superclass, func=None, descriptor_cls=None):
    """
    Returns a suitable contribute_to_class() method for the Field subclass.

    If 'func' is passed in, it is the existing contribute_to_class() method on
    the subclass and it is called before anything else. It is assumed in this
    case that the existing contribute_to_class() calls all the necessary
    superclass methods.

    If descriptor_cls is passed, an instance of that class will be used;
    otherwise uses the descriptor class `Creator`.
    """
    if descriptor_cls is None:
        descriptor_cls = Creator

    def contribute_to_class(self, cls, name):
        if func:
            func(self, cls, name)
        else:
            super(superclass, self).contribute_to_class(cls, name)
        setattr(cls, self.name, descriptor_cls(self))

    return contribute_to_class
