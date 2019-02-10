from __future__ import absolute_import
import types
import functools

def lxml_extension(method=None, ns_uri=None, name=None):
    """
    Decorator for registering model methods as lxml extensions to be passed
    to XPathFields and XsltFields.

    Params:

        ns_uri (optional): The namespace uri for the function. If used in an
                           XPathField, this uri will need to be one of the
                           values in the namespaces attr of the XmlModel's
                           `Meta` class. If used in an XSLT, the namespace
                           will need to be defined in the xslt file or string.

                           Defaults to the value of the `extension_ns_uri`
                           attr of the XmlModel's `Meta` class, if defined.

        name (optional): The name of the function to register. Defaults to
                         the method's name.

    Usage:

        import math
        from pprint import pprint
        from djlxml import XmlModel, xmlfields, lxml_extension

        class PrimeExample(XmlModel):

            class Meta:
                namespaces = {
                    'f': 'urn:local:myfuncs',
                }

            @lxml_extension(ns_uri='urn:local:myfuncs')
            def sqrt(self, context, nodes):
                nodelist = []
                for node in nodes:
                    nodestr = getattr(node, 'text', node)
                    nodefloat = float(nodestr)
                    nodelist.append(repr(math.sqrt(nodefloat)))
                return nodelist

            square_roots = xmlfields.XPathFloatListField('f:sqrt(/prime_numbers/num)')

        primes = u'''
            <prime_numbers>
                <num>2</num>
                <num>3</num>
                <num>5</num>
                <num>7</num>
            </prime_numbers>'''.strip()

        example = PrimeExample.create_from_string(primes)
        pprint(example.square_roots)
        '''
        [1.4142135623730951,
         1.7320508075688772,
         2.2360679774997898,
         2.6457513110645907]
        '''
    """


    # If called without a method, we've been called with optional arguments.
    # We return a decorator with the optional arguments filled in.
    # Next time round we'll be decorating method.
    if method is None:
        return functools.partial(lxml_extension, ns_uri=ns_uri, name=name)

    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        return method(self, *args, **kwargs)
        
    if name is None:
        if isinstance(method, types.MethodType):
            name = method.__func__.__name__
        else:
            name = method.__name__

    wrapper.is_lxml_extension = True
    wrapper.lxml_ns_uri = ns_uri
    wrapper.lxml_extension_name = name

    return wrapper
