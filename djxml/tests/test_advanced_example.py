from __future__ import absolute_import
import os
from doctest import Example

from lxml import etree
from lxml.doctestcompare import LXMLOutputChecker

from django import test

from .xmlmodels import AtomFeed, AtomEntry


class TestAdvancedExample(test.TestCase):

    @classmethod
    def setUpClass(cls):
        super(TestAdvancedExample, cls).setUpClass()
        cls.example = AtomFeed.create_from_file(
            os.path.join(os.path.dirname(__file__), 'data', 'atom_feed.xml'))

    def assertXmlEqual(self, got, want):
        checker = LXMLOutputChecker()
        if not checker.check_output(want, got, 0):
            message = checker.output_difference(Example("", want), got, 0)
            raise AssertionError(message)

    def test_feed_title(self):
        self.assertEqual(self.example.title, "Example Feed")

    def test_feed_entry_title(self):
        self.assertIsInstance(self.example.entries[0], AtomEntry)
        self.assertEqual(self.example.entries[0].title, "An example entry")

    def test_transform_to_rss(self):
        expected = "\n".join([
            '<rss version="2.0">',
            '  <channel><description>Example Feed</description>',
            '',
            '  <link>http://example.org/</link>',
            '  <pubDate>Thu, 05 Jul 2012 18:30:02Z</pubDate>',
            '',
            '  <item>',
            '',
            '    <link>http://example.org/2003/12/13/atom03</link>',
            '    <guid>urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a</guid>',
            '    <pubDate>Thu, 05 Jul 2012 18:30:02Z</pubDate>',
            '    <description>&lt;div&gt;Some text.&lt;/div&gt;</description>',
            '  </item>',
            '</channel>',
            '</rss>\n'])
        self.assertXmlEqual(expected, etree.tounicode(self.example.transform_to_rss()))
