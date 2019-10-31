django-xml
##########

.. image:: https://travis-ci.org/theatlantic/django-xml.svg?branch=master
    :target: https://travis-ci.org/theatlantic/django-xml


**django-xml** is a python module which provides an abstraction to
`lxml <http://lxml.de/>`_'s XPath and XSLT functionality in a manner
resembling django database models.

Note
====

* Version 2.0 drops support for Django < 1.11
* Version 2.0.1 drops support for Python 3.4
* Version 3.0 will drop support for Python < 3.5


Installation
============

To install the latest stable release of django-xml, use pip or
easy\_install

::

    pip install django-xml
    easy_install django-xml

For the latest development version, install from source with pip:

::

    pip install -e git+git://github.com/theatlantic/django-xml#egg=django-xml

If the source is already checked out, install via setuptools:

::

    python setup.py develop

Example
=======

::

    import math
    from djxml import xmlmodels

    class NumbersExample(xmlmodels.XmlModel):

        class Meta:
            extension_ns_uri = "urn:local:number-functions"
            namespaces = {"fn": extension_ns_uri,}

        all_numbers  = xmlmodels.XPathIntegerListField("//num")
        even_numbers = xmlmodels.XPathIntegerListField("//num[fn:is_even(.)]")
        sqrt_numbers = xmlmodels.XPathFloatListField("fn:sqrt(//num)")

        @xmlmodels.lxml_extension
        def is_even(self, context, number_nodes):
            numbers = [getattr(n, 'text', n) for n in number_nodes]
            return all([bool(int(num) % 2 == 0) for num in numbers])

        @xmlmodels.lxml_extension
        def sqrt(self, context, number_nodes):
            sqrts = []
            for number_node in number_nodes:
                number = getattr(number_node, 'text', number_node)
                sqrts.append(repr(math.sqrt(int(number))))
            return sqrts

    def main():
        numbers_xml = u"""
        <numbers>
            <num>1</num>
            <num>2</num>
            <num>3</num>
            <num>4</num>
            <num>5</num>
            <num>6</num>
            <num>7</num>
        </numbers>"""

        example = NumbersExample.create_from_string(numbers_xml)

        print "all_numbers  = %r" % example.all_numbers
        print "even_numbers = %r" % example.even_numbers
        print "sqrt_numbers = [%s]" % ', '.join(['%.3f' % n for n in example.sqrt_numbers])
        # all_numbers  = [1, 2, 3, 4, 5, 6, 7]
        # even_numbers = [2, 4, 6]
        # sqrt_numbers = [1.000, 1.414, 1.732, 2.000, 2.236, 2.449, 2.646]

    if __name__ == '__main__':
        main()

Advanced Example
================

An example of django-xml usage which includes XsltField and
@lxml\_extension methods can be found
`here <https://github.com/theatlantic/django-xml/blob/master/docs/advanced_example.md>`_.

API Documentation
=================

`Read API documentation on github <https://github.com/theatlantic/django-xml#api-documentation>`_
