from __future__ import absolute_import
from django import test

from .xmlmodels import NumbersExample


class TestExamples(test.TestCase):

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

    def test_all_numbers(self):
        example = NumbersExample.create_from_string(self.numbers_xml)
        self.assertEqual(example.all_numbers, [1, 2, 3, 4, 5, 6, 7])

    def test_lxml_boolean_extension(self):
        example = NumbersExample.create_from_string(self.numbers_xml)
        self.assertEqual(example.even_numbers, [2, 4, 6])

    def test_lxml_list_extension(self):
        example = NumbersExample.create_from_string(self.numbers_xml)
        self.assertEqual(example.square_numbers,
            [1, 4, 9, 16, 25, 36, 49])
