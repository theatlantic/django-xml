import re
import sys
import codecs

from lxml import etree

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db.models.base import subclass_exception
from django.utils.encoding import smart_str, force_unicode

from .options import Options

from .loading import register_xml_models, get_xml_model


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
        new_class = super_new(cls, name, bases, {'__module__': module})
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

        new_class.add_to_class('_meta', Options(meta, **kwargs))

        new_class.add_to_class('DoesNotExist', subclass_exception('DoesNotExist',
                tuple(x.DoesNotExist
                        for x in parents if hasattr(x, '_meta') and not x._meta.abstract)
                                or (ObjectDoesNotExist,), module))
        new_class.add_to_class('MultipleObjectsReturned', subclass_exception('MultipleObjectsReturned',
                tuple(x.MultipleObjectsReturned
                        for x in parents if hasattr(x, '_meta') and not x._meta.abstract)
                                or (MultipleObjectsReturned,), module))

        # Bail out early if we have already created this class.
        m = get_xml_model(new_class._meta.app_label, name, False)
        if m is not None:
            return m

        # Add all attributes to the class.
        for obj_name, obj in attrs.items():
            new_class.add_to_class(obj_name, obj)

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


class XmlModel(object):

    __metaclass__ = XmlModelBase

    def __init__(self, element_tree):
        fields_iter = iter(self._meta.fields)

        for field in fields_iter:
            if getattr(field, 'is_primary_etree', True):
                val = element_tree
            else:
                val = field.get_default()
            setattr(self, field.attname, val)

        super(XmlModel, self).__init__()

    def _get_etree_val(self, meta=None):
        if not meta:
            meta = self._meta
        return getattr(self, meta.etree.attname)

    @classmethod
    def create_from_string(cls, xml_source):
        opts = cls._meta
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
            u = unicode(self)
        except (UnicodeEncodeError, UnicodeDecodeError):
            u = '[Bad Unicode data]'
        return smart_str(u'<%s: %s>' % (self.__class__.__name__, u))

    def __str__(self):
        if hasattr(self, '__unicode__'):
            return force_unicode(self).encode('utf-8')
        return '%s object' % self.__class__.__name__

    def __eq__(self, other):
        return isinstance(other, self.__class__) \
            and self._get_etree_val() == other._get_etree_val()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self._get_etree_val())
