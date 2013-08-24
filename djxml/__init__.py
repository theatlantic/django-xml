try:
    __version__ = __import__('pkg_resources').get_distribution('django-xml').version
except Exception:
    __version__ = 'unknown'
