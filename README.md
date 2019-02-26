# django-xml

[![Build Status](https://travis-ci.org/theatlantic/django-xml.svg?branch=master)](https://travis-ci.org/theatlantic/django-xml)


**django-xml** is a python module which provides an abstraction to
[lxml](http://lxml.de/)'s XPath and XSLT functionality in a manner resembling
django database models.

## Contents

 * [Installation](#installation)
 * [Example](#example)
 * [Advanced Example](#advanced-example)
 * [XmlModel Meta options](#xmlmodel-meta-options)
   * [namespaces](#namespacesoptionsnamespaces--)
   * [parser_opts](#parser_optsoptionsparser_opts--)
   * [extension_ns_uri](#extension_ns_urioptionsextension_ns_uri)
 * [@lxml_extension reference](#lxml_extension-reference)
   * [ns_uri](#ns_uri)
   * [name](#name)
 * [XPathField options](#xpathfield-options)
   * [xpath_query](#xpath_queryxpathfieldxpath_query)
   * [required](#requiredxpathfieldrequired)
   * [extra_namespaces](#extra_namespacesxpathfieldextra_namespaces)
   * [extensions](#extensionsxpathfieldextensions)
 * [XPathSingleNodeField options](#xpathsinglenodefield-options)
   * [ignore_extra_nodes](#ignore_extra_nodesxpathsinglenodefieldignore_extra_nodes--false)
 * [XsltField options](#xsltfield-options)
   * [xslt_file, xslt_string](#xslt_file-xslt_stringxsltfieldxslt_filexsltfieldxslt_string)
   * [parser](#parserxsltfieldparser)
   * [extensions](#extensionsxsltfieldextensions--)
 * [XmlModel field reference](#xmlmodel-field-reference)

## Installation

To install the latest stable release of django-xml, use pip or easy_install

```bash
pip install django-xml
easy_install django-xml
```

For the latest development version, install from source with pip:

```bash
pip install -e git+git://github.com/theatlantic/django-xml#egg=django-xml
```

If the source is already checked out, install via setuptools:

```bash
python setup.py develop
```

## Example

```python
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
```

## Advanced Example

An example of django-xml usage which includes XsltField and @lxml_extension methods
can be found [here](https://github.com/theatlantic/django-xml/blob/master/docs/advanced_example.md).

## XmlModel Meta options

Metadata for an <b>`XmlModel`</b> is passed as attributes of an
internal class named <b>`Meta`</b>. Listed below are the options
that can be set on the <b>`Meta`</b> class.

#### namespaces<br>`Options.namespaces = {}`

A dict of prefix / namespace URIs key-value pairs that is passed to
[`lxml.etree.XPathEvaluator()`](http://lxml.de/api/lxml.etree-module.html#XPathEvaluator)
for all XPath fields on the model.

#### parser_opts<br>`Options.parser_opts = {}`

A dict of keyword arguments to pass to
[lxml.etree.XMLParser()](http://lxml.de/api/lxml.etree.XMLParser-class.html)

#### extension_ns_uri<br>`Options.extension_ns_uri`

The default namespace URI to use for extension functions created using the
<b>`@lxml_extension`</b> decorator.

## @lxml_extension reference

<pre lang="python">def lxml_extension(method=None, ns_uri=None, name=None)</pre>

The <b>`@lxml_extension`</b> decorator is for registering model methods as
lxml extensions which can be used in XPathFields and XsltFields. All keyword
arguments to it are optional.

#### ns_uri

The namespace uri for the function. If used in an <b>`XPathField`</b>, this uri will need to
be one of the values in the namespaces attribute of the XmlModel's internal
<b>`Meta`</b> class. If used in an XSLT, the namespace will need to be defined in
the xslt file or string.

Defaults to the value of the <b>`extension_ns_uri`</b> attribute of the
XmlModel's internal <b>`Meta`</b> class, if defined. If neither the
<b>`extension_ns_uri`</b> attribute of XmlModel.Meta is set, nor is the
<b>`ns_uri`</b> keyword argument passed, an <b>`ExtensionNamespaceException`</b>
will be thrown.

#### name

The name of the function to register. Defaults to the method's name.

## XPathField options

The following arguments are available to all XPath field types. All but the
first are optional.


#### xpath_query<br>`XPathField.xpath_query`

The XPath query string to perform on the document. Required.

#### required<br>`XPathField.required = True`

If `True`, a `DoesNotExist` exception will be thrown if no nodes match the
XPath query for the field. Defaults to `True`.

#### extra_namespaces<br>`XPathField.extra_namespaces`

A dict of extra prefix/uri namespace pairs to pass to
[`lxml.etree.XPathEvaluator()`](http://lxml.de/api/lxml.etree-module.html#XPathEvaluator).

#### extensions<br>`XPathField.extensions`

Extra extensions to pass on to
[`lxml.etree.XSLT`](http://lxml.de/api/lxml.etree-module.html#XPathEvaluator).
See the [lxml documentation](http://lxml.de/extensions.html#evaluator-local-extensions)
for details on how to form the <b>`extensions`</b> keyword argument.

## XPathSingleNodeField options

#### ignore_extra_nodes<br>`XPathSingleNodeField.ignore_extra_nodes = False`

If `True` return only the first node of the XPath evaluation result, even if it
evaluates to more than one node. If `False`, accessing an xpath field which
evaluates to more than one node will throw a `MultipleObjectsExist` exception
Defaults to `False`.

To return the full list of nodes, Use an <b>`XPathListField`</b>

## XsltField options

#### xslt_file, xslt_string<br>`XsltField.xslt_file`<br>`XsltField.xslt_string`

The first positional argument to XsltField is the path to an xslt file.
Alternatively, the xslt can be passed as a string using the
<b>`xslt_string`</b> keyword argument. It is required to specify one of these
fields.

#### parser<br>`XsltField.parser`

An instance of [lxml.etree.XMLParser](http://lxml.de/api/lxml.etree.XMLParser-class.html)
to override the one created by the XmlModel class. To override parsing options
for the entire class, use the [<b>`parser_opts`</b>](#parser_optsoptionsparser_opts--)
attribute of the [XmlModel internal <b>`Meta`</b> class](#xmlmodel-meta-options).

#### extensions<br>`XsltField.extensions = {}`

Extra extensions to pass on to the constructor of
[`lxml.etree.XSLT`](http://lxml.de/api/lxml.etree.XSLT-class.html#__init__).
See the [lxml documentation](http://lxml.de/extensions.html#evaluator-local-extensions)
for details on how to form the <b>`extensions`</b> keyword argument.

## XmlModel field reference

```python
class XsltField(xslt_file=None, xslt_string=None, parser=None, extensions=None)
```

Field which abstracts the creation of
[lxml.etree.XSLT](http://lxml.de/api/lxml.etree.XSLT-class.html) objects.
This field's return type is a callable which accepts keyword arguments that
are passed as parameters to the stylesheet.

```python
class XPathField(xpath_query, required=False, extra_namespaces=None, extensions=None)
```

Base field for abstracting the retrieval of node results from the xpath
evaluation of an xml etree.

```python
class XPathField(xpath_query, required=False, extra_namespaces=None, extensions=None)
```

Base field for abstracting the retrieval of node results from the xpath
evaluation of an xml etree.

```python
class XPathListField(xpath_query, required=False, extra_namespaces=None, extensions=None)
```

Field which abstracts retrieving a list of nodes from the xpath evaluation
of an xml etree.

```python
class XPathSingleItemField(xpath_query, required=False, extra_namespaces=None,
                           extensions=None, ignore_extra_nodes=False)
```

Field which abstracts retrieving the first node result from the xpath
evaluation of an xml etree.

```python
class XPathTextField(XPathSingleNodeField)
```

Returns a unicode value when accessed.

```python
class XPathIntegerField(XPathSingleNodeField)
```

Returns an int value when accessed.

```python
class XPathFloatField(XPathSingleNodeField)
```

Returns a float value when accessed.

```python
class XPathDateTimeField(XPathSingleNodeField)
```

Returns a datetime.datetime value when accessed.

```python
class XPathTextListField(XPathListField)
```

Returns a list of unicode values when accessed.

```python
class XPathIntegerListField(XPathListField)
```

Returns a list of int values when accessed.

```python
class XPathFloatListField(XPathListField)
```

Returns a list of float values when accessed.

```python
class XPathDateTimeListField(XPathListField)
```

Returns a list of datetime.datetime values when accessed.
