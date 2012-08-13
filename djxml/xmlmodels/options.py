from bisect import bisect

from lxml import etree

from django.db.models.fields import FieldDoesNotExist
from django.utils.datastructures import SortedDict
from django.utils.encoding import smart_str

from .exceptions import ExtensionNamespaceException
from .fields import XmlPrimaryElementField

DEFAULT_NAMES = ('app_label', 'namespaces', 'parser_opts', 'extension_ns_uri',
                 'xsd_schema', 'xsd_schema_file',)


class Options(object):

    def __init__(self, meta, app_label=None, namespaces=None, parser_opts=None,
                 extension_ns_uri=None, xsd_schema=None, xsd_schema_file=None):
        self.local_fields = []
        self.module_name = None
        self.object_name, self.app_label = None, app_label
        self.meta = meta

        self.root = None
        self.has_root_field, self.root_field = False, None

        # Dict mapping ns prefixes to ns URIs
        self.namespaces = namespaces or {}

        # Default namespace uri for functions passed as extensions to
        # XSLT/XPath
        self.extension_ns_uri = extension_ns_uri

        # Extensions generated by XmlModelBase.add_to_class()
        self.extensions = {}

        # An instance of lxml.etree.XMLSchema, can be set in Meta
        self.xsd_schema = xsd_schema
        # The path to an xml schema file, can be set in Meta
        self.xsd_schema_file = xsd_schema_file

        # Dict passed as kwargs to create lxml.etree.XMLParser instance
        self.parser_opts = parser_opts or {}
        self.parser = None
        self.parents = SortedDict()

    def contribute_to_class(self, cls, name):
        cls._meta = self
        # First, construct the default values for these options.
        self.object_name = cls.__name__
        self.module_name = self.object_name.lower()

        # Next, apply any overridden values from 'class Meta'.
        if self.meta:
            meta_attrs = self.meta.__dict__.copy()
            for name in self.meta.__dict__:
                # Ignore any private attributes that Django doesn't care about
                # NOTE: We can't modify a dictionary's contents while looping
                # over it, so we loop over the *original* dictionary instead.
                if name.startswith('_'):
                    del meta_attrs[name]
            for attr_name in DEFAULT_NAMES:
                if attr_name in meta_attrs:
                    setattr(self, attr_name, meta_attrs.pop(attr_name))
                elif hasattr(self.meta, attr_name):
                    setattr(self, attr_name, getattr(self.meta, attr_name))

            # Any leftover attributes must be invalid.
            if meta_attrs != {}:
                raise TypeError("'class Meta' got invalid attribute(s): %s" \
                    % ','.join(meta_attrs.keys()))
                if self.xsd_schema is not None and self.xsd_schema_file is not None:
                    raise TypeError("'class Meta' got attribute 'xsd_schema' "
                                     "and 'xsd_schema_file'; only one may be "
                                     "specified.")
                if self.schema and not isinstance(self.schema, etree.XMLSchema):
                    raise TypeError("'class Meta' got attribute 'xsd_schema' "
                                   "of type %r, expected lxml.etree.XMLSchema" \
                                    % self.xsd_schema.__class.__name)

        del self.meta

    def _prepare(self, model):
        if not self.has_root_field:
            root_field = XmlPrimaryElementField()
            model.add_to_class('root', root_field)
        if self.xsd_schema_file is not None:
            schema_root = etree.parse(self.xsd_schema_file)
            self.xsd_schema = etree.XMLSchema(schema_root)

    def get_parser(self):
        if self.parser is None:
            self.parser = etree.XMLParser(**self.parser_opts)
        return self.parser

    def add_field(self, field):
        # Insert the given field in the order in which it was created, using
        # the "creation_counter" attribute of the field.
        self.local_fields.insert(bisect(self.local_fields, field), field)
        self.setup_root(field)
        if hasattr(self, '_field_cache'):
            del self._field_cache
            del self._field_name_cache

        if hasattr(self, '_name_map'):
            del self._name_map

    def add_extension(self, method, extension_name=None):
        if method.lxml_extension_name is not None:
            extension_name = method.lxml_extension_name

        ns_uri = method.lxml_ns_uri
        if ns_uri is None:
            if self.extension_ns_uri is not None:
                ns_uri = self.extension_ns_uri
            else:
                msg = ("Extension %r has no extension_ns_uri defined and %r "
                       "does not define a default extension namespace uri") \
                    % (extension_name, self.app_label)
                raise ExtensionNamespaceException(msg)
        
        self.extensions[(ns_uri, extension_name,)] = method

    def setup_root(self, field):
        if not self.root and field.is_root_field:
            self.etree = field

    def __repr__(self):
        return '<Options for %s>' % self.object_name

    def __str__(self):
        return "%s.%s" % (smart_str(self.app_label), smart_str(self.module_name))

    def _fields(self):
        """
        The getter for self.fields. This returns the list of field objects
        available to this model.

        Callers are not permitted to modify this list, since it's a reference
        to this instance (not a copy).
        """
        try:
            self._field_name_cache
        except AttributeError:
            self._fill_fields_cache()
        return self._field_name_cache
    fields = property(_fields)

    def _fill_fields_cache(self):
        cache = []
        for parent in self.parents:
            for field in parent._meta.fields:
                cache.append(field)
        cache.extend([f for f in self.local_fields])
        self._field_name_cache = tuple(cache)

    def get_field(self, name):
        """
        Returns the requested field by name. Raises FieldDoesNotExist on error.
        """
        for f in self.fields:
            if f.name == name:
                return f
        raise FieldDoesNotExist('%s has no field named %r' \
            % (self.object_name, name))
