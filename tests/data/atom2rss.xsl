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
