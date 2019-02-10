from __future__ import absolute_import
import re
import time
import os
from datetime import datetime
from lxml import etree

from djxml import xmlmodels


class NumbersExample(xmlmodels.XmlModel):

    class Meta:
        extension_ns_uri = "urn:local:number-functions"
        namespaces = {"fn": extension_ns_uri,}

    all_numbers  = xmlmodels.XPathIntegerListField("//num")
    even_numbers = xmlmodels.XPathIntegerListField("//num[fn:is_even(.)]")
    square_numbers = xmlmodels.XPathIntegerListField("fn:square(//num)")

    @xmlmodels.lxml_extension
    def is_even(self, context, number_nodes):
        numbers = [getattr(n, 'text', n) for n in number_nodes]
        return all([bool(int(num) % 2 == 0) for num in numbers])

    @xmlmodels.lxml_extension
    def square(self, context, number_nodes):
        squares = []
        for number_node in number_nodes:
            number = getattr(number_node, 'text', number_node)
            squares.append(repr(int(number) ** 2))
        return squares


strip_namespaces = etree.XSLT(etree.XML("""
<x:stylesheet version="1.0" xmlns:x="http://www.w3.org/1999/XSL/Transform"
              xmlns:xhtml="http://www.w3.org/1999/xhtml">
  <x:output encoding="utf-8" method="xml"/>
  <x:template match="@*|node()"><x:copy><x:apply-templates/></x:copy></x:template>
  <x:template match="xhtml:*"><x:element name="{local-name()}"><x:apply-templates/></x:element></x:template>
</x:stylesheet>"""))


class AtomEntry(xmlmodels.XmlModel):

    class Meta:
        extension_ns_uri = "urn:local:atom-feed-functions"
        namespaces = {
            "fn":   extension_ns_uri,
            "atom": "http://www.w3.org/2005/Atom",
        }

    @xmlmodels.lxml_extension
    def escape_xhtml(self, context, nodes):
        return u"".join([etree.tounicode(strip_namespaces(n)) for n in nodes])

    title = xmlmodels.XPathTextField('atom:title')
    entry_id = xmlmodels.XPathTextField('atom:id')
    updated = xmlmodels.XPathDateTimeField('atom:updated')
    summary = xmlmodels.XPathInnerHtmlField('fn:escape_xhtml(atom:summary)')


class AtomFeed(xmlmodels.XmlModel):

    class Meta:
        extension_ns_uri = "urn:local:atom-feed-functions"
        namespaces = {
            "fn":   extension_ns_uri,
            "atom": "http://www.w3.org/2005/Atom",
        }

    title = xmlmodels.XPathTextField("/atom:feed/atom:title")

    updated = xmlmodels.XPathDateTimeField("/atom:feed/atom:*[%s]" \
        % "local-name()='updated' or (local-name()='published' and not(../atom:updated))")

    entries = xmlmodels.EmbeddedXPathListField(AtomEntry,
        "/atom:feed/atom:entry", required=False)

    transform_to_rss = xmlmodels.XsltField(
        os.path.join(os.path.dirname(__file__), "data", "atom2rss.xsl"))

    @xmlmodels.lxml_extension
    def escape_xhtml(self, context, nodes):
        return u"".join([etree.tounicode(strip_namespaces(n)) for n in nodes])

    @xmlmodels.lxml_extension
    def convert_atom_date_to_rss(self, context, rfc3339_str):
        try:
            m = re.match(r"([\d:T-]+)(?:\.\d+)?(Z|[+-][\d:]{5})", rfc3339_str)
        except TypeError:
            return ""
        dt_str, tz_str = m.groups()
        dt = datetime(*[t for t in time.strptime(dt_str, "%Y-%m-%dT%H:%M:%S")][0:6])
        tz_str = 'Z' if tz_str == 'Z' else tz_str[:3] + tz_str[4:]
        return dt.strftime("%a, %d %b %Y %H:%M:%S") + tz_str
