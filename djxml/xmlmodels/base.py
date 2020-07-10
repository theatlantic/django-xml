from __future__ import absolute_import
import re
import sys
import codecs
import functools
import copy
import six

from lxml import etree

from django.core.exceptions import (ObjectDoesNotExist, FieldError,
                                    MultipleObjectsReturned,)
from django.db.models.base import subclass_exception
from django.utils.encoding import force_text
from django.utils.encoding import smart_bytes, smart_text

from .signals import xmlclass_prepared
from .options import Options, DEFAULT_NAMES
from .loading import register_xml_models, get_xml_model

# Alias smart_str based on Python version
smart_str = smart_text if six.PY3 else smart_bytes


class XmlModelBase(type):
    """
    Metaclass for xml models.
    """

    def __new__(cls, name, bases, attrs):
        super_new = super(XmlModelBase, cls).__new__
        parents = [b for b in bases if isinstance(b, XmlModelBase)]
        if not parents:
            # If this isn't a subclass of Model, don't do anything special.
            return super_new(cls, name, bases, attrs)

        # Create the class.
        module = attrs.pop('__module__')
        new_attrs = {'__module__': module}
        classcell = attrs.pop('__classcell__', None)
        if classcell is not None:
            new_attrs['__classcell__'] = classcell
        new_class = super_new(cls, name, bases, new_attrs)

        attr_meta = attrs.pop('Meta', None)
        if not attr_meta:
            meta = getattr(new_class, 'Meta', None)
        else:
            meta = attr_meta

        if getattr(meta, 'app_label', None) is None:
            # Figure out the app_label by looking one level up.
            # For 'django.contrib.sites.models', this would be 'sites'.
            model_module = sys.modules[new_class.__module__]
            kwargs = {"app_label": model_module.__name__.split('.')[-2]}
        else:
            kwargs = {}

        for attr_name in DEFAULT_NAMES:
            if attr_name == 'app_label':
                continue
            if getattr(meta, attr_name, None) is None:
                for base in parents:
                    if not hasattr(base, '_meta'):
                        continue
                    attr_val = getattr(base._meta, attr_name)
                    if attr_val is not None:
                        kwargs[attr_name] = attr_val
                        break

        new_class.add_to_class('_meta', Options(meta, **kwargs))

        new_class.add_to_class(
            'DoesNotExist',
            subclass_exception(
                'DoesNotExist',
                tuple(
                    x.DoesNotExist for x in parents if hasattr(x, '_meta')
                ) or (ObjectDoesNotExist,),
                module,
                attached_to=new_class))
        new_class.add_to_class(
            'MultipleObjectsReturned',
            subclass_exception(
                'MultipleObjectsReturned',
                tuple(
                    x.MultipleObjectsReturned for x in parents if hasattr(x, '_meta')
                ) or (MultipleObjectsReturned,),
                module,
                attached_to=new_class))

        # Bail out early if we have already created this class.
        m = get_xml_model(new_class._meta.app_label, name, False)
        if m is not None:
            return m

        # Add all attributes to the class.
        for obj_name, obj in attrs.items():
            new_class.add_to_class(obj_name, obj)

        field_names = set([f.name for f in new_class._meta.local_fields])

        for base in parents:
            if not hasattr(base, '_meta'):
                # Things without _meta aren't functional models, so they're
                # uninteresting parents
                continue

            for field in base._meta.local_fields:
                if field.name in field_names:
                    raise FieldError('Local field %r in class %r clashes '
                                     'with field of similar name from '
                                     'base class %r' %
                                        (field.name, name, base.__name__))
                new_class.add_to_class(field.name, copy.deepcopy(field))

            new_class._meta.parents.update(base._meta.parents)

        new_class._prepare()
        register_xml_models(new_class._meta.app_label, new_class)

        # Because of the way imports happen (recursively), we may or may not be
        # the first time this model tries to register with the framework. There
        # should only be one class for each model, so we always return the
        # registered version.
        return get_xml_model(new_class._meta.app_label, name, False)

    def add_to_class(cls, name, value):
        if hasattr(value, 'contribute_to_class'):
            value.contribute_to_class(cls, name)
        else:
            setattr(cls, name, value)
            if getattr(value, 'is_lxml_extension', False):
                cls._meta.add_extension(value, extension_name=name)

    def _prepare(cls):
        """
        Creates some methods once self._meta has been populated.
        """
        opts = cls._meta
        opts._prepare(cls)

        # Give the class a docstring -- its definition.
        if cls.__doc__ is None:
            cls.__doc__ = "%s(%s)" % (cls.__name__, ", ".join([f.attname for f in opts.fields]))

        xmlclass_prepared.send(sender=cls)


@six.add_metaclass(XmlModelBase)
class XmlModel(object):

    def __init__(self, root_element_tree):
        fields_iter = iter(self._meta.fields)

        for field in fields_iter:
            if getattr(field, 'is_root_field', False):
                val = root_element_tree
            else:
                val = None
            setattr(self, field.attname, val)

        super(XmlModel, self).__init__()

    def _get_etree_val(self, meta=None):
        if not meta:
            meta = self._meta
        return getattr(self, meta.etree.attname)

    _default_xpath_eval = None

    @property
    def default_xpath_eval(self):
        if self._default_xpath_eval is None:
            self._default_xpath_eval = self._get_xpath_eval()
        return self._default_xpath_eval

    def _merge_xpath_kwargs(self, ns=None, ext=None):
        """
        Merge user-provided namespace and extension keywords with the model
        defaults.
        """
        opts = self._meta

        xpath_kwargs = {
            'namespaces': getattr(opts, 'namespaces', {}),
            'extensions': dict([(k, functools.partial(method, self))
                                for k, method in six.iteritems(opts.extensions)]),}

        if ns is not None:
            xpath_kwargs['namespaces'].update(ns)
        if ext is not None:
            xpath_kwargs['extensions'].update(ext)
        return xpath_kwargs

    def _get_xpath_eval(self, namespaces=None, extensions=None):
        xpath_kwargs = self._merge_xpath_kwargs(ns=namespaces, ext=extensions)
        return etree.XPathEvaluator(self._get_etree_val(), **xpath_kwargs)

    def xpath(self, query, namespaces=None, extensions=None):
        """
        Evaluate and return the results of an XPath query expression on the
        xml model.

        query:      The XPath query string
        namespaces: (optional) dict of extra prefix/uri namespaces pairs to
                    pass to lxml.etree.XPathEvaluator()
        extensions: (optional) Extra extensions to pass on to
                    lxml.etree.XPathEvaluator()
        """
        if namespaces is None and extensions is None:
            xpath_eval = self.default_xpath_eval
        else:
            xpath_eval = self._get_xpath_eval(ns=namespaces, ext=extensions)
        return xpath_eval(query)

    @classmethod
    def create_from_string(cls, xml_source, parser=None):
        opts = cls._meta
        if parser is None:
            parser = opts.get_parser()
        # lxml doesn't like it when the <?xml ?> header has an encoding,
        # so we strip out encoding="utf-8" with a regex
        xml_source = re.sub(r'(<\?xml[^\?]*?) encoding="(?:utf-8|UTF-8)"([^\?]*?\?>)',
                            r'\1\2', xml_source)
        tree = etree.XML(xml_source, parser)
        return cls(tree)

    @classmethod
    def create_from_file(cls, xml_file):
        with codecs.open(xml_file, encoding='utf-8', mode='r') as f:
            xml_source = f.read()
        return cls.create_from_string(xml_source)

    def __repr__(self):
        try:
            u = six.text_type(self)
        except (UnicodeEncodeError, UnicodeDecodeError):
            u = '[Bad Unicode data]'
        return smart_str(u'<%s: %s>' % (self.__class__.__name__, u))

    def __str__(self):
        if hasattr(self, '__unicode__'):
            return force_text(self).encode('utf-8')
        return '%s object' % self.__class__.__name__

    def __eq__(self, other):
        return isinstance(other, self.__class__) \
            and self._get_etree_val() == other._get_etree_val()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self._get_etree_val())
