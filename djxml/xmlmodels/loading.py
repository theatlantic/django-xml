"""
Utilities for loading xml_models and the modules that contain them.

More or less identical to django.db.models.loading, with a few db
specific things removed.
"""

from __future__ import absolute_import
from importlib import import_module
from collections import OrderedDict

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import module_has_submodule

import sys
import os
import threading
import six

__all__ = ('get_apps', 'get_app', 'get_xml_models', 'get_xml_model',
        'register_xml_models', 'load_app', 'app_cache_ready')

class AppCache(object):
    """
    A cache that stores installed applications and their xml_models. Used to
    provide reverse-relations and for app introspection (e.g. admin).
    """
    # Use the Borg pattern to share state between all instances. Details at
    # http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/66531.
    __shared_state = dict(
        # Keys of app_store are the xml_model modules for each application.
        app_store = OrderedDict(),

        # Mapping of app_labels to a dictionary of xml_model names to model
        # code.
        app_xml_models = OrderedDict(),

        # Mapping of app_labels to errors raised when trying to import the app
        app_errors = {},

        # -- Everything below here is only used when populating the cache --
        loaded = False,
        handled = {},
        postponed = [],
        nesting_level = 0,
        write_lock = threading.RLock(),
        _get_xml_models_cache = {},
    )

    def __init__(self):
        self.__dict__ = self.__shared_state

    def _populate(self):
        """
        Fill in all the cache information. This method is threadsafe, in the
        sense that every caller will see the same state upon return, and if
        the cache is already initialised, it does not work.
        """
        if self.loaded:
            return
        self.write_lock.acquire()
        try:
            if self.loaded:
                return
            for app_name in settings.INSTALLED_APPS:
                if app_name in self.handled:
                    continue
                self.load_app(app_name, True)
            if not self.nesting_level:
                for app_name in self.postponed:
                    self.load_app(app_name)
                self.loaded = True
        finally:
            self.write_lock.release()

    def load_app(self, app_name, can_postpone=False):
        """
        Loads the app with the provided fully qualified name, and returns the
        xml model module.
        """
        self.handled[app_name] = None
        self.nesting_level += 1
        app_module = import_module(app_name)
        try:
            xml_models = import_module('.xml_models', app_name)
        except ImportError:
            self.nesting_level -= 1
            # If the app doesn't have an xml_models module, we can just ignore
            # the ImportError and return no xml_models for it.
            if not module_has_submodule(app_module, 'xml_models'):
                return None
            # But if the app does have an xml_models module, we need to figure
            # out whether to suppress or propagate the error. If can_postpone
            # is True then it may be that the package is still being imported
            # by Python and the xml_models module isn't available yet. So we
            # add the app to the postponed list and we'll try it again after
            # all the recursion has finished (in populate). If can_postpone is
            # False then it's time to raise the ImportError.
            else:
                if can_postpone:
                    self.postponed.append(app_name)
                    return None
                else:
                    raise

        self.nesting_level -= 1
        if xml_models not in self.app_store:
            self.app_store[xml_models] = len(self.app_store)
        return xml_models

    def app_cache_ready(self):
        """
        Returns true if the xml model cache is fully populated.

        Useful for code that wants to cache the results of get_xml_models()
        for themselves once it is safe to do so.
        """
        return self.loaded

    def get_apps(self):
        "Returns a list of all installed modules that contain xml models."
        self._populate()

        # Ensure the returned list is always in the same order (with new apps
        # added at the end). This avoids unstable ordering on the admin app
        # list page, for example.
        apps = [(v, k) for k, v in self.app_store.items()]
        apps.sort()
        return [elt[1] for elt in apps]

    def get_app(self, app_label, emptyOK=False):
        """
        Returns the module containing the xml models for the given app_label.
        If the app has no xml models in it and 'emptyOK' is True, returns None
        """
        self._populate()
        self.write_lock.acquire()
        try:
            for app_name in settings.INSTALLED_APPS:
                if app_label == app_name.split('.')[-1]:
                    mod = self.load_app(app_name, False)
                    if mod is None:
                        if emptyOK:
                            return None
                    else:
                        return mod
            raise ImproperlyConfigured("App with label %s could not be found"\
                % app_label)
        finally:
            self.write_lock.release()

    def get_app_errors(self):
        "Returns the map of known problems with the INSTALLED_APPS."
        self._populate()
        return self.app_errors

    def get_xml_models(self, app_mod=None, include_deferred=False):
        """
        Given a module containing xml models, returns a list of the xml_models
        Otherwise returns a list of all installed xml_models.

        By default, xml models created to satisfy deferred attribute
        queries are *not* included in the list of xml models. However, if
        you specify include_deferred, they will be.
        """
        cache_key = (app_mod, False, include_deferred)
        try:
            return self._get_xml_models_cache[cache_key]
        except KeyError:
            pass
        self._populate()
        if app_mod:
            app_list = [self.app_xml_models.get(app_mod.__name__.split('.')[-2], OrderedDict())]
        else:
            app_list = six.itervalues(self.app_xml_models)
        xml_model_list = []
        for app in app_list:
            xml_model_list.extend(
                model for model in app.values()
                if ((not model._deferred or include_deferred))
            )
        self._get_xml_models_cache[cache_key] = xml_model_list
        return xml_model_list

    def get_xml_model(self, app_label, model_name, seed_cache=True):
        """
        Returns the xml model matching the given app_label and
        case-insensitive model_name.

        Returns None if no xml model is found.
        """
        if seed_cache:
            self._populate()
        return self.app_xml_models.get(app_label, OrderedDict()).get(
            model_name.lower())

    def register_xml_models(self, app_label, *xml_models):
        """
        Register a set of xml models as belonging to an app.
        """
        for model in xml_models:
            # Store as 'name: model' pair in a dictionary
            # in the app_models dictionary
            model_name = model._meta.object_name.lower()
            model_dict = self.app_xml_models.setdefault(app_label, OrderedDict())
            if model_name in model_dict:
                # The same model may be imported via different paths (e.g.
                # appname.xml_models and project.appname.xml_models). We use the
                # source filename as a means to detect identity.
                fname1 = os.path.abspath(sys.modules[model.__module__].__file__)
                fname2 = os.path.abspath(sys.modules[model_dict[model_name].__module__].__file__)
                # Since the filename extension could be .py the first time and
                # .pyc or .pyo the second time, ignore the extension when
                # comparing.
                if os.path.splitext(fname1)[0] == os.path.splitext(fname2)[0]:
                    continue
            model_dict[model_name] = model
        self._get_xml_models_cache.clear()

cache = AppCache()

# These methods were always module level, so are kept that way for backwards
# compatibility.
get_apps = cache.get_apps
get_app = cache.get_app
get_app_errors = cache.get_app_errors
get_xml_models = cache.get_xml_models
get_xml_model = cache.get_xml_model
register_xml_models = cache.register_xml_models
load_app = cache.load_app
app_cache_ready = cache.app_cache_ready
