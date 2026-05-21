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
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import pytest
from ged4py.parser import GedcomReader

from gedcom2gtr import main, Person


HERE = Path(__file__).resolve().parent


GEDCOM_HEADER = """
    0 HEAD
    1 GEDC
    2 VERS 5.5.1
    2 FORM LINEAGE-LINKED
    1 CHAR UTF-8
    1 LANG English
"""

GEDCOM_FOOTER = """
    0 TRLR
"""


def prepare_gedcom(s):
    return "\n".join(stripped for line in s.splitlines() if (stripped := line.lstrip()))


@contextmanager
def gedcom_reader(gedcom):
    gedcom = prepare_gedcom(GEDCOM_HEADER + "\n" + gedcom + "\n" + GEDCOM_FOOTER)
    with GedcomReader(io.BytesIO(gedcom.encode("utf-8"))) as reader:
        yield reader


class TestPerson:
    @pytest.mark.parametrize(
        "gedcom, expected",
        (
            # No names
            ("", None),
            # Flat name with a single given name
            (
                """
                1 NAME Given1
                """,
                r"{\pref{Given1} \surn{?}}",
            ),
            # Flat name with a single surname
            (
                """
                1 NAME /Sur1/
                """,
                r"{\pref{?} \surn{Sur1}}",
            ),
            # Flat name with a single given name and a surname
            (
                """
                1 NAME Given1 /Sur1/
                """,
                r"{\pref{Given1} \surn{Sur1}}",
            ),
            # Flat name with the surname inbetween given names. This is an
            # explicit example in the annotated GEDCOM 5.5.5 spec.
            (
                """
                1 NAME Given1 /Sur1/ Given2
                """,
                r"{\pref{Given1} \surn{Sur1} Given2}",
            ),
            # Nested name with only a given name
            (
                """
                1 NAME Should-be-ignored
                2 GIVN Given1, Given2
                """,
                r"{\pref{Given1 Given2} \surn{?}}",
            ),
            # Nested name with only a rufname
            (
                """
                1 NAME Should-be-ignored
                2 _RUFNAME Ruf1, Ruf2
                """,
                r"{\pref{Ruf1 Ruf2} \surn{?}}",
            ),
            # Nested name with only a nickname
            (
                """
                1 NAME Should-be-ignored
                2 NICK Nick1, Nick2
                """,
                r"{\pref{?} \nick{Nick1 Nick2} \surn{?}}",
            ),
            # Nested name with only a surname
            (
                """
                1 NAME Should-be-ignored
                2 SURN Sur1, Sur2
                """,
                r"{\pref{?} \surn{Sur1 Sur2}}",
            ),
            # Nested name with a given name and a rufname
            (
                """
                1 NAME Should-be-ignored
                2 GIVN Given1, Given2
                2 _RUFNAME Ruf1, Ruf2
                """,
                r"{Given1 Given2 \pref{Ruf1 Ruf2} \surn{?}}",
            ),
            # Nested name with a given name, a rufname, and a nickname
            (
                """
                1 NAME Should-be-ignored
                2 GIVN Given1, Given2
                2 _RUFNAME Ruf1, Ruf2
                2 NICK Nick1, Nick2
                """,
                (
                    r"{Given1 Given2 \pref{Ruf1 Ruf2} \nick{Nick1 Nick2} "
                    r"\surn{?}}"
                ),
            ),
            # Nested name with a given name, a rufname, and a surname
            (
                """
                1 NAME Should-be-ignored
                2 GIVN Given1, Given2
                2 _RUFNAME Ruf1, Ruf2
                2 SURN Sur1, Sur2
                """,
                r"{Given1 Given2 \pref{Ruf1 Ruf2} \surn{Sur1 Sur2}}",
            ),
            # Nested name with a given name, a rufname, a nickname, and a
            # surname
            (
                """
                1 NAME Should-be-ignored
                2 GIVN Given1, Given2
                2 _RUFNAME Ruf1, Ruf2
                2 NICK Nick1, Nick2
                2 SURN Sur1, Sur2
                """,
                r"{Given1 Given2 \pref{Ruf1 Ruf2} \nick{Nick1 Nick2} \surn{Sur1 Sur2}}",
            ),
            # Multiple names
            (
                """
                1 NAME Given1
                1 NAME Given2
                """,
                r"{\pref{Given1} \surn{?}}",
            ),
        ),
    )
    def test_parse_names(self, gedcom, expected):
        with gedcom_reader("0 @I0001@ INDI\n" + gedcom) as reader:
            indi_record = next(iter(reader.records0("INDI")))
            assert Person._parse_names(indi_record) == expected


class TestMain:
    def run(self, fn, args, xref_id):
        args = ["gedcom2gtr"] + [str(arg) for arg in args] + [str(fn), str(xref_id)]
        with patch("sys.argv", args):
            with redirect_stdout(io.StringIO()) as stdout:
                try:
                    main()
                except SystemExit as e:
                    assert e.code == 0
        return stdout.getvalue()

    def check(self, ged_fn, args, xref_id, output_fn):
        expected_output = (HERE / output_fn).read_text().strip()
        assert self.run(HERE / ged_fn, args, xref_id) == expected_output

    def test_defaults(self):
        self.check("basics.ged", [], "I0006", "default.graph")

    def test_no_siblings(self):
        self.check("basics.ged", ["--no-siblings"], "I0006", "no_siblings.graph")

    def test_no_ancestor_siblings(self):
        self.check("basics.ged", ["--no-ancestor-siblings"], "I0006", "no_ancestor_siblings.graph")

    @pytest.mark.parametrize("max_ancestor_generations", [0, 1, 2, 3])
    def test_max_ancestor_generations(self, max_ancestor_generations):
        self.check(
            "basics.ged",
            ["--max-ancestor-generations", max_ancestor_generations],
            "I0006",
            f"max_ancestor_generations_{max_ancestor_generations}.graph",
        )

    @pytest.mark.parametrize("max_descendant_generations", [0, 1, 2, 3])
    def test_max_descendant_generations(self, max_descendant_generations):
        self.check(
            "basics.ged",
            ["--max-descendant-generations", max_descendant_generations],
            "I0006",
            f"max_descendant_generations_{max_descendant_generations}.graph",
        )

    def test_dynamic_generation_limits_with_fewer_ancestors(self):
        self.check(
            "basics.ged",
            [
                "--max-ancestor-generations",
                "3",
                "--max-descendant-generations",
                "1",
                "--dynamic-generation-limits",
            ],
            "I0006",
            "default.graph",
        )

    def test_dynamic_generation_limits_with_fewer_descendants(self):
        self.check(
            "basics.ged",
            [
                "--max-ancestor-generations",
                "1",
                "--max-descendant-generations",
                "3",
                "--dynamic-generation-limits",
            ],
            "I0006",
            "default.graph",
        )

    def test_multiple_families(self):
        self.check("multiple_families.ged", [], "I0002", "multiple_families.graph")
