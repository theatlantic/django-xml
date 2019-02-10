from __future__ import absolute_import
from django.dispatch import Signal

xmlclass_prepared = Signal(providing_args=["class"])
