#!/usr/bin/env python

# Copyright (c) 2020-2026 Florian Brucker (www.florianbrucker.de)
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

from contextlib import redirect_stdout
import io
from pathlib import Path
from unittest.mock import patch

import pytest

from gedcom2gtr import main


HERE = Path(__file__).resolve().parent


def run(fn, args, xref_id):
    args = ['gedcom2gtr'] + [str(arg) for arg in args] + [str(fn), str(xref_id)]
    with patch("sys.argv", args):
        with redirect_stdout(io.StringIO()) as stdout:
            try:
                main()
            except SystemExit as e:
                assert e.code == 0
    return stdout.getvalue()


def check(ged_fn, args, xref_id, output_fn):
    expected_output = (HERE / output_fn).read_text().strip()
    assert run(HERE / ged_fn, args, xref_id) == expected_output


def test_defaults():
    check("basics.ged", [], 'I0006', "default.graph")


def test_no_siblings():
    check("basics.ged", ['--no-siblings'], 'I0006', "no_siblings.graph")


def test_no_ancestor_siblings():
    check(
        "basics.ged",
        ['--no-ancestor-siblings'],
        'I0006',
        "no_ancestor_siblings.graph",
    )


@pytest.mark.parametrize("max_ancestor_generations", [0, 1, 2, 3])
def test_max_ancestor_generations(max_ancestor_generations):
    check(
        "basics.ged",
        ['--max-ancestor-generations', max_ancestor_generations],
        'I0006',
        f"max_ancestor_generations_{max_ancestor_generations}.graph",
    )


@pytest.mark.parametrize("max_descendant_generations", [0, 1, 2, 3])
def test_max_descendant_generations(max_descendant_generations):
    check(
        "basics.ged",
        ['--max-descendant-generations', max_descendant_generations],
        'I0006',
        f'max_descendant_generations_{max_descendant_generations}.graph',
    )


def test_dynamic_generation_limits_with_fewer_ancestors():
    check(
        "basics.ged",
        [
            '--max-ancestor-generations', '3',
            '--max-descendant-generations', '1',
            '--dynamic-generation-limits',
        ],
        'I0006',
        "default.graph",
    )


def test_dynamic_generation_limits_with_fewer_descendants():
    check(
        "basics.ged",
        [
            '--max-ancestor-generations', '1',
            '--max-descendant-generations', '3',
            '--dynamic-generation-limits',
        ],
        'I0006',
        "default.graph",
    )


def test_multiple_families():
    check('multiple_families.ged', [], 'I0002', "multiple_families.graph")
