#!/usr/bin/env python

# Copyright (c) 2020 Florian Brucker (www.florianbrucker.de)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""
Tests for ``gedcom2gtr``.
"""

from pathlib import Path
import subprocess


HERE = Path(__file__).resolve().parent

TEST_GED = HERE / 'test.ged'


def run(args, xref_id):
    args = ['gedcom2gtr'] + args + [str(TEST_GED), str(xref_id)]
    p = subprocess.run(args, capture_output=True, check=True, encoding='utf-8')
    return p.stdout


def check(args, xref_id, expected_output):
    assert run(args, xref_id) == expected_output


DEFAULT_OUTPUT = r'sandclock[id=F0002]{child[id=F0003]{g[id=I0006]{name={\pref{D} \surn{1}},sex={male},}child[id=F0004]{g[id=I0008]{name={\pref{E} \surn{1}},sex={male},}p[id=I0009]{name={\pref{F} \surn{1}},sex={female},}c[id=I0010]{name={\pref{G} \surn{1}},}}}parent[id=F0001]{g[id=I0004]{name={\pref{B} \surn{2}},sex={male},}p[id=I0001]{name={\pref{A} \surn{1}},birth={(AD)1900-01-01}{Somewhere},sex={male},}p[id=I0002]{name={\pref{A} \surn{2}},birth-={(AD)1895-12-31},sex={female},}c[id=I0003]{name={\pref{B} \surn{1}},}}p[id=I0005]{name={\pref{C} \surn{1}},sex={female},}c[id=I0007]{name={\pref{D} \surn{2}},}}'  # noqa: E501


def test_defaults():
    check([], 'I0006', DEFAULT_OUTPUT)


def test_no_siblings():
    check(
        ['--no-siblings'],
        'I0006',
        r'sandclock[id=F0002]{child[id=F0003]{g[id=I0006]{name={\pref{D} \surn{1}},sex={male},}child[id=F0004]{g[id=I0008]{name={\pref{E} \surn{1}},sex={male},}p[id=I0009]{name={\pref{F} \surn{1}},sex={female},}c[id=I0010]{name={\pref{G} \surn{1}},}}}parent[id=F0001]{g[id=I0004]{name={\pref{B} \surn{2}},sex={male},}p[id=I0001]{name={\pref{A} \surn{1}},birth={(AD)1900-01-01}{Somewhere},sex={male},}p[id=I0002]{name={\pref{A} \surn{2}},birth-={(AD)1895-12-31},sex={female},}c[id=I0003]{name={\pref{B} \surn{1}},}}p[id=I0005]{name={\pref{C} \surn{1}},sex={female},}}',  # noqa: E501
    )


def test_no_ancestor_siblings():
    check(
        ['--no-ancestor-siblings'],
        'I0006',
        r'sandclock[id=F0002]{child[id=F0003]{g[id=I0006]{name={\pref{D} \surn{1}},sex={male},}child[id=F0004]{g[id=I0008]{name={\pref{E} \surn{1}},sex={male},}p[id=I0009]{name={\pref{F} \surn{1}},sex={female},}c[id=I0010]{name={\pref{G} \surn{1}},}}}parent[id=F0001]{g[id=I0004]{name={\pref{B} \surn{2}},sex={male},}p[id=I0001]{name={\pref{A} \surn{1}},birth={(AD)1900-01-01}{Somewhere},sex={male},}p[id=I0002]{name={\pref{A} \surn{2}},birth-={(AD)1895-12-31},sex={female},}}p[id=I0005]{name={\pref{C} \surn{1}},sex={female},}c[id=I0007]{name={\pref{D} \surn{2}},}}',  # noqa: E501
    )


def test_max_ancestor_generations():
    check(
        ['--max-ancestor-generations', '1'],
        'I0006',
        r'sandclock[id=F0002]{child[id=F0003]{g[id=I0006]{name={\pref{D} \surn{1}},sex={male},}child[id=F0004]{g[id=I0008]{name={\pref{E} \surn{1}},sex={male},}p[id=I0009]{name={\pref{F} \surn{1}},sex={female},}c[id=I0010]{name={\pref{G} \surn{1}},}}}parent[id=F0001]{g[id=I0004]{name={\pref{B} \surn{2}},sex={male},}}p[id=I0005]{name={\pref{C} \surn{1}},sex={female},}c[id=I0007]{name={\pref{D} \surn{2}},}}',  # noqa: E501
    )


def test_no_ancestor_generations():
    check(
        ['--max-ancestor-generations', '0'],
        'I0006',
        r'sandclock[id=F0002]{child[id=F0003]{g[id=I0006]{name={\pref{D} \surn{1}},sex={male},}child[id=F0004]{g[id=I0008]{name={\pref{E} \surn{1}},sex={male},}p[id=I0009]{name={\pref{F} \surn{1}},sex={female},}c[id=I0010]{name={\pref{G} \surn{1}},}}}}',  # noqa: E501
    )


def test_max_descendant_generations():
    check(
        ['--max-descendant-generations', '1'],
        'I0006',
        r'sandclock[id=F0002]{child[id=F0003]{g[id=I0006]{name={\pref{D} \surn{1}},sex={male},}c[id=I0008]{name={\pref{E} \surn{1}},sex={male},}}parent[id=F0001]{g[id=I0004]{name={\pref{B} \surn{2}},sex={male},}p[id=I0001]{name={\pref{A} \surn{1}},birth={(AD)1900-01-01}{Somewhere},sex={male},}p[id=I0002]{name={\pref{A} \surn{2}},birth-={(AD)1895-12-31},sex={female},}c[id=I0003]{name={\pref{B} \surn{1}},}}p[id=I0005]{name={\pref{C} \surn{1}},sex={female},}c[id=I0007]{name={\pref{D} \surn{2}},}}',  # noqa: E501
    )


def test_no_descendant_generations():
    check(
        ['--max-descendant-generations', '0'],
        'I0006',
        r'sandclock[id=F0002]{c[id=I0006]{name={\pref{D} \surn{1}},sex={male},}parent[id=F0001]{g[id=I0004]{name={\pref{B} \surn{2}},sex={male},}p[id=I0001]{name={\pref{A} \surn{1}},birth={(AD)1900-01-01}{Somewhere},sex={male},}p[id=I0002]{name={\pref{A} \surn{2}},birth-={(AD)1895-12-31},sex={female},}c[id=I0003]{name={\pref{B} \surn{1}},}}p[id=I0005]{name={\pref{C} \surn{1}},sex={female},}c[id=I0007]{name={\pref{D} \surn{2}},}}',  # noqa: E501
    )


def test_dynamic_generation_limits_with_fewer_ancestors():
    check(
        [
            '--max-ancestor-generations', '3',
            '--max-descendant-generations', '1',
            '--dynamic-generation-limits',
        ],
        'I0006',
        DEFAULT_OUTPUT,
    )


def test_dynamic_generation_limits_with_fewer_descendants():
    check(
        [
            '--max-ancestor-generations', '1',
            '--max-descendant-generations', '3',
            '--dynamic-generation-limits',
        ],
        'I0006',
        DEFAULT_OUTPUT,
    )
