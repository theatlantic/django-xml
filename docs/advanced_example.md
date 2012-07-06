# Advanced Example

## myapp/xmlmodels.py

```python
import re, time
from datetime import datetime
from os.path import dirname, join
from lxml import etree
from djxml import xmlmodels

strip_namespaces = etree.XSLT(etree.XML("""
<x:stylesheet version="1.0" xmlns:x="http://www.w3.org/1999/XSL/Transform"
              xmlns:xhtml="http://www.w3.org/1999/xhtml">
  <x:output encoding="utf-8" method="xml"/>
  <x:template match="@*|node()"><x:copy><x:apply-templates/></x:copy></x:template>
  <x:template match="xhtml:*"><x:element name="{local-name()}"><x:apply-templates/></x:element></x:template>
</x:stylesheet>"""))


class AtomFeed(xmlmodels.XmlModel):

    class Meta:
        extension_ns_uri = "urn:local:atom-feed-functions"
        namespaces = {
            "fn":   extension_ns_uri,
            "atom": "http://www.w3.org/2005/Atom",
        }

    feed_title = xmlmodels.XPathTextField("/atom:feed/atom:title")

    updated = xmlmodels.XPathDateTimeField("/atom:feed/atom:*[%s]" \
        % "local-name()='updated' or (local-name()='published' and not(../atom:updated))")

    entries = xmlmodels.XPathListField("/atom:feed/atom:entry", required=False)

    titles = xmlmodels.XPathTextListField("/atom:feed/atom:entry/atom:title",
                                          required=False)

    transform_to_rss = xmlmodels.XsltField(join(dirname(__file__), "atom2rss.xsl"))

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


def test():
    atom_xml_file = join(dirname(__file__), 'atom_feed.xml')
    atom_feed = AtomFeed.create_from_file(atom_xml_file)
    rss_feed = atom_feed.transform_to_rss()
    print u"\n".join([
        u"feed_title  = %r" % atom_feed.feed_title,
        u"updated     = %r" % atom_feed.updated,
        u"num_entries = %d" % len(atom_feed.entries),
        u"titles      = %r" % (u", ".join(atom_feed.titles)), u"",])
    print u"rss = %s" % etree.tounicode(rss_feed)
```

## myapp/atom_feed.xml

```xml
<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:xhtml="http://www.w3.org/1999/xhtml">
  <title>Example Feed</title>
  <link rel="alternate" href="http://example.org/"/>
  <updated>2012-07-05T18:30:02Z</updated>
  <id>urn:uuid:60a76c80-d399-11d9-b93C-0003939e0af6</id>
  <entry>
    <title>An example entry</title>
    <link rel="alternate" href="http://example.org/2003/12/13/atom03"/>
    <id>urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a</id>
    <updated>2012-07-05T18:30:02Z</updated>
    <summary type="xhtml"><xhtml:div>Some text.</xhtml:div></summary>
  </entry>
</feed>
```

## myapp/atom2rss.xsl

```xml
<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:atom="http://www.w3.org/2005/Atom"
                xmlns:fn="urn:local:atom-feed-functions"
                version="1.0" exclude-result-prefixes="atom fn">
  <xsl:output encoding="utf-8" indent="yes" method="xml" media-type="application/rss+xml"/>
  <xsl:template match="atom:*"/>
  <xsl:template match="/atom:feed">
    <rss version="2.0">
      <channel>
        <xsl:call-template name="author" />
        <description><xsl:value-of select="atom:title"/></description>
        <xsl:apply-templates/>
      </channel>
    </rss>
  </xsl:template>
  <xsl:template match="atom:link[@rel='alternate']"><link><xsl:value-of select="@href"/></link></xsl:template>
  <xsl:template match="atom:entry/atom:id"><guid><xsl:value-of select="."/></guid></xsl:template>
  <xsl:template match="atom:entry"><item><xsl:call-template name="author"/><xsl:apply-templates/></item></xsl:template>
  <xsl:template match="atom:summary">
    <description>
      <xsl:choose>
        <xsl:when test="@type='xhtml'">
          <xsl:value-of select="fn:escape_xhtml(child::node())"/>
        </xsl:when>
        <xsl:otherwise><xsl:value-of select="."/></xsl:otherwise>
      </xsl:choose>        
    </description>
  </xsl:template>
  <xsl:template match="atom:updated">
    <pubDate>
      <xsl:value-of select="fn:convert_atom_date_to_rss(string(.))"/>
    </pubDate>
  </xsl:template>
  <xsl:template name="author">
    <xsl:variable name="emails" select="atom:email|/atom:feed/atom:author[./atom:email][1]/atom:email" />
    <xsl:if test="count($emails) &gt; 0"><author><xsl:value-of select="$emails[1]" /></author></xsl:if>
  </xsl:template>
</xsl:stylesheet>
```