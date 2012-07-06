from bisect import bisect

from lxml import etree

from django.db.models.fields import FieldDoesNotExist
from django.utils.encoding import smart_str

from .exceptions import ExtensionNamespaceException
from .fields import XmlPrimaryElementField

DEFAULT_NAMES = ('app_label', 'namespaces', 'parser_opts', 'extension_ns_uri',)

class Options(object):

    def __init__(self, meta, app_label=None):
        self.local_fields = []
        self.module_name = None
        self.object_name, self.app_label = None, app_label
        self.meta = meta

        self.etree = None
        self.has_primary_etree_field, self.etree_field = False, None

        # Dict mapping ns prefixes to ns URIs
        self.namespaces = {}

        # Default namespace uri for functions passed as extensions to
        # XSLT/XPath
        self.extension_ns_uri = None

        # Extensions generated by XmlModelBase.add_to_class()
        self.extensions = {}

        # Dict passed as kwargs to create lxml.etree.XMLParser instance
        self.parser_opts = {}
        self.parser = None

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

        del self.meta

    def _prepare(self, model):
        if self.etree is None:
            etree = XmlPrimaryElementField()
            model.add_to_class('primary_element', etree)

    def get_parser(self):
        if self.parser is None:
            self.parser = etree.XMLParser(**self.parser_opts)
        return self.parser

    def add_field(self, field):
        # Insert the given field in the order in which it was created, using
        # the "creation_counter" attribute of the field.
        self.local_fields.insert(bisect(self.local_fields, field), field)
        self.setup_etree(field)
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

    def setup_etree(self, field):
        if not self.etree and field.is_primary_etree:
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
