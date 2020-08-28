#!/usr/bin/env python

"""
Create databases for the genealogytree LaTeX package from GEDCOM files.

The LaTeX genealogytree package (GTR) provides tools for including
genealogy trees in LaTeX documents. One way of doing that is by storing
the genealogical information in a GTR-specific database file. This tool
allows you to create such databases from GEDCOM files (GEDCOM is a
popular file format for storing genealogical information).
"""

from dataclasses import dataclass
import datetime as dt
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ged4py.date import DateValue, DateValueVisitor
from ged4py.model import Individual
from ged4py.parser import GedcomReader


# The gtr-package only supports a certain subset of family trees. In
# particular, trees can only grow upwards or downwards, but not both
# ways. An exception is the "sandclock" format, which allows for the
# ancestors and descendants (and their siblings) of a single person.


#: Maps GEDCOM month names to their number
_MONTH_NAME_TO_NUMBER = {
    'JAN': 1,
    'FEB': 2,
    'MAR': 3,
    'APR': 4,
    'MAY': 5,
    'JUN': 6,
    'JUL': 7,
    'AUG': 8,
    'SEP': 9,
    'OCT': 10,
    'NOV': 11,
    'DEC': 12,
}


class GtrDateFormatter(DateValueVisitor):
    """
    Visitor class that produces GTR string representation of dates.
    """
    def visitSimple(self, date):
        return self._format_date(date.date)

    def visitPeriod(self, date):
        return f'{self._format_date(date.date1)}/{self._format_date(date.date2)}'

    visitRange = visitPeriod

    def visitFrom(self, date):
        return f'{self._format_date(date.date)}/'

    visitAfter = visitFrom

    def visitTo(self, date):
        return f'/{self._format_date(date.date)}'

    visitBefore = visitTo

    def visitAbout(self, date):
        return self._format_date(date.date, True)

    visitCalculated = visitAbout
    visitEstimated = visitAbout
    visitInterpreted = visitAbout

    def visitPhrase(self, date):
        return None

    def format(self, date_value) -> str:
        return date_value.accept(self)

    def _format_date(self, date, uncertain: bool = False) -> str:
        calender = 'AD'
        year = date.year
        if year < 0:
            year = -year
            calender = 'BC'
        if uncertain:
            calender = f'ca{calender}'
        parts = [str(year)]
        if date.month:
            parts.append(f'{_MONTH_NAME_TO_NUMBER[date.month]:02d}')
            if date.day:
                parts.append(f'{date.day:02d}')
        timestamp = '-'.join(parts)
        return f'({calender}){timestamp}'


@dataclass
class Person:
    id: str
    gtr_fields: Dict[str, str]
    parent_families: List['Family']
    child_family: Optional['Family']

    @classmethod
    def from_indi(cls, indi) -> 'Person':
        """
        Create a person from a ``ged4py`` individual.
        """
        date_formatter = GtrDateFormatter()
        gtr_fields = {}

        names = {
            name_record.type: name_record.value[:2]
            for name_record in indi.sub_tags('NAME')
        }
        for key in ['maiden', 'birth', None, 'married']:
            name = names.get(key)
            if name:
                gtr_fields['name'] = rf'{{\pref{{{name[0] or "?"}}} \surn{{{name[1] or "?"}}}}}'
                break

        birth_date = indi.sub_tag_value('BIRT/DATE')
        if birth_date:
            gtr_fields['birth-'] = f'{{{date_formatter.format(birth_date)}}}'
        # TODO: Support for birth location

        death_date = indi.sub_tag_value('DEAT/DATE')
        if death_date:
            gtr_fields['death-'] = f'{{{date_formatter.format(death_date)}}}'
        # TODO: Support for death location

        sex = indi.sub_tag_value('SEX')
        if sex:
            gtr_fields['sex'] = '{female}' if sex == 'F' else '{male}'

        return cls(
            indi.xref_id.replace('@', ''),
            gtr_fields,
            [],
            None,
        )

    def to_gtr(self, node_type: str, include_id: bool = False) -> str:
        """
        Convert to GTR-string.
        """
        parts = [node_type]
        if include_id:
            parts.append(f'[id={self.id}]')
        parts.append('{')
        for key, value in self.gtr_fields.items():
            parts.append(f'{key}={value},')
        parts.append('}')
        return ''.join(parts)

    def __repr__(self):
        return f'<{self.__class__.__name__} id={self.id!r}>'


@dataclass
class Family:
    id: str
    parents: List[Person]
    children: List[Person]

    def __repr__(self):
        return f'<{self.__class__.__name__} id={self.id!r}>'

    # TODO: Support for marriage event


def load_gedcom(fn: Path) -> Tuple[List[Person], List[Family]]:
    # ged4py 0.2.2 has problems with hashing, see
    # https://github.com/andy-z/ged4py/issues/22
    # Our workaround is to use the xref_id instead.
    indi_to_person = {}
    families = []
    with GedcomReader(fn) as reader:
        # First pass, create persons
        for indi in reader.records0('INDI'):
            #print(indi)
            person = Person.from_indi(indi)
            indi_to_person[indi.xref_id] = person
            #print(person.to_gtr('g'))
            #print()

        #print()
        #print('***')
        #print()

        # Second pass, create families
        for fam in reader.records0('FAM'):
            parents = []
            for tag in ['HUSB', 'WIFE']:
                indi = fam.sub_tag(tag)
                if indi:
                    parents.append(indi_to_person[indi.xref_id])
            children = [
                indi_to_person[indi.xref_id]
                for indi in fam.sub_tags('CHIL')
            ]
            family = Family(
                fam.xref_id.replace('@', ''),
                parents,
                children,
            )
            families.append(family)
            for parent in parents:
                parent.parent_families.append(family)
            for child in children:
                assert child.child_family is None
                child.child_family = family

    return list(indi_to_person.values()), families


def get_parent_family(person: Person) -> Optional[Family]:
    if person.parent_families:
        if len(person.parent_families) > 1:
            # TODO: Support for multiple parent families
            print(f'WARNING: Multiple parent families')
        return person.parent_families[0]


def child_node(person: Person) -> str:
    parent_family = get_parent_family(person)
    if not parent_family:
        return person.to_gtr('c', True)
    parts = [
        f'child[id={parent_family.id}]{{',
        person.to_gtr('g', True),
    ]
    for parent in parent_family.parents:
        if parent != person:
            parts.append(parent.to_gtr('p', True))
    for child in parent_family.children:
        parts.append(child_node(child))
    parts.append('}')
    return ''.join(parts)


def parent_node(person: Person) -> str:
    child_family = person.child_family
    if not child_family:
        return person.to_gtr('p', True)
    parts = [
        f'parent[id={child_family.id}]{{',
        person.to_gtr('g', True),
        _parent_node_body(person),
        '}',
    ]
    return ''.join(parts)


def _parent_node_body(person: Person) -> str:
    parts = []
    if person.child_family:
        for parent in person.child_family.parents:
            parts.append(parent_node(parent))
        for child in person.child_family.children:
            if child != person:
                parts.append(child.to_gtr('c', True))
    return ''.join(parts)


def sandclock_node(person: Person) -> str:
    return ''.join([
        'sandclock{',
        child_node(person),
        _parent_node_body(person),
        '}',
    ])


if __name__ == '__main__':
    import sys
    persons, families = load_gedcom(sys.argv[1])
    print(sandclock_node(persons[0]))
