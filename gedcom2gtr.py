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
import logging
from pathlib import Path
import sys
from typing import BinaryIO, Dict, List, Optional, TextIO, Tuple, Union

import click
from ged4py.calendar import CalendarDate
from ged4py.date import DateValue, DateValueVisitor
from ged4py.model import Individual, Record
from ged4py.parser import GedcomReader


log = logging.getLogger('gedcom2gtr')


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
    def visitSimple(self, date: DateValue) -> str:
        return self._format_date(date.date)

    def visitPeriod(self, date: DateValue) -> str:
        return f'{self._format_date(date.date1)}/{self._format_date(date.date2)}'

    visitRange = visitPeriod

    def visitFrom(self, date: DateValue) -> str:
        return f'{self._format_date(date.date)}/'

    visitAfter = visitFrom

    def visitTo(self, date: DateValue) -> str:
        return f'/{self._format_date(date.date)}'

    visitBefore = visitTo

    def visitAbout(self, date: DateValue) -> str:
        return self._format_date(date.date, True)

    visitCalculated = visitAbout
    visitEstimated = visitAbout
    visitInterpreted = visitAbout

    def visitPhrase(self, date: DateValue) -> str:
        return ''

    def format(self, date: DateValue) -> str:
        return date.accept(self)

    def _format_date(self, date: CalendarDate, uncertain: bool = False) -> str:
        calendar = 'BC' if date.bc else 'AD'
        if uncertain:
            calendar = f'ca{calendar}'
        parts = [str(date.year)]
        if date.month:
            parts.append(f'{_MONTH_NAME_TO_NUMBER[date.month]:02d}')
            if date.day:
                parts.append(f'{date.day:02d}')
        timestamp = '-'.join(parts)
        return f'({calendar}){timestamp}'


_date_formatter = GtrDateFormatter()


@dataclass
class Event:
    date: Optional[DateValue]
    place: Optional[str]

    @classmethod
    def from_record(cls, record: Optional[Record]) -> 'Event':
        return cls(
            record.sub_tag_value('DATE') if record else None,
            record.sub_tag_value('PLAC') if record else None,
        )

    def __bool__(self):
        return bool(self.date or self.place)

    def to_gtr(self) -> Tuple[str, str]:
        date = _date_formatter.format(self.date) if self.date else ''
        if self.place:
            return '', f'{{{date}}}{{{self.place}}}'
        return '-', f'{{{date}}}'


@dataclass
class Person:
    id: str
    gtr_fields: Dict[str, str]
    parent_families: List['Family']
    child_family: Optional['Family']

    @classmethod
    def from_record(cls, record: Record) -> 'Person':
        """
        Create a person from a ``ged4py`` individual.
        """
        gtr_fields = {}

        names = {
            name_record.type: name_record.value[:2]
            for name_record in record.sub_tags('NAME')
        }
        for key in ['maiden', 'birth', None, 'married']:
            name = names.get(key)
            if name:
                gtr_fields['name'] = rf'{{\pref{{{name[0] or "?"}}} \surn{{{name[1] or "?"}}}}}'
                break

        for key, tag in [
            ('birth', 'BIRT'),
            ('death', 'DEAT'),
        ]:
            event = Event.from_record(record.sub_tag(tag))
            if event:
                modifier, value = event.to_gtr()
                gtr_fields[f'{key}{modifier}'] = value

        sex = record.sub_tag_value('SEX')
        if sex:
            gtr_fields['sex'] = '{female}' if sex == 'F' else '{male}'

        occupation = record.sub_tag_value('OCCU')
        if occupation:
            gtr_fields['profession'] = f'{{{occupation}}}'

        return cls(
            record.xref_id.replace('@', ''),
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

    def count_ancestor_generations(self) -> int:
        num = -1
        if self.child_family:
            for parent in self.child_family.parents:
                num = max(num, parent.count_ancestor_generations())
        return num + 1

    def count_descendant_generations(self) -> int:
        num = -1
        for parent_family in self.parent_families:
            for child in parent_family.children:
                num = max(num, child.count_descendant_generations())
        return num + 1


@dataclass
class Family:
    id: str
    parents: List[Person]
    children: List[Person]
    marriage: Event

    def __repr__(self):
        return f'<{self.__class__.__name__} id={self.id!r}>'

    def make_gtr_options(self) -> str:
        option_parts = [f'id={self.id}']
        if self.marriage:
            modifier, value = self.marriage.to_gtr()
            option_parts.append(f'family database={{marriage{modifier}={value}}}')
        return ','.join(option_parts)


def load_gedcom(
    f: Union[Path, BinaryIO],
) -> Tuple[Dict[str, Person], Dict[str, Family]]:
    # ged4py 0.2.2 has problems with hashing, see
    # https://github.com/andy-z/ged4py/issues/22
    # Our workaround is to use the xref_id instead.
    id_to_person = {}
    id_to_family = {}
    with GedcomReader(f) as reader:
        # First pass, create persons
        for indi in reader.records0('INDI'):
            person = Person.from_record(indi)
            id_to_person[person.id] = person

        # Second pass, create families
        for fam in reader.records0('FAM'):
            parents = []
            for tag in ['HUSB', 'WIFE']:
                indi = fam.sub_tag(tag)
                if indi:
                    parents.append(id_to_person[indi.xref_id.replace('@', '')])
            children = [
                id_to_person[indi.xref_id.replace('@', '')]
                for indi in fam.sub_tags('CHIL')
            ]
            marriage = Event.from_record(fam.sub_tag('MARR'))
            family = Family(
                fam.xref_id.replace('@', ''),
                parents,
                children,
                marriage,
            )
            id_to_family[family.id] = family
            for parent in parents:
                parent.parent_families.append(family)
            for child in children:
                assert child.child_family is None
                child.child_family = family

    return id_to_person, id_to_family


def get_parent_family(person: Person) -> Optional[Family]:
    if person.parent_families:
        if len(person.parent_families) > 1:
            # TODO: Support for multiple parent families
            print(f'WARNING: Multiple parent families')
        return person.parent_families[0]


def _child_node(person: Person, max_generations: int = -1) -> str:
    parent_family = get_parent_family(person)
    if not parent_family or max_generations == 0:
        # No known spouse/children or recursion limit reached
        return person.to_gtr('c', True)
    parts = [
        f'child[{parent_family.make_gtr_options()}]{{',
        person.to_gtr('g', True),
    ]
    for parent in parent_family.parents:
        if parent != person:
            parts.append(parent.to_gtr('p', True))
    for child in parent_family.children:
        parts.append(_child_node(child, max(-1, max_generations - 1)))
    parts.append('}')
    return ''.join(parts)


def _parent_node(
    person: Person,
    include_siblings: bool = True,
    include_ancestor_siblings: bool = True,
    max_generations: int = -1,
) -> str:
    child_family = person.child_family
    if not child_family or max_generations == 0:
        # Parents unknown or recursion limit reached
        return person.to_gtr('p', True)
    parts = [
        f'parent[{child_family.make_gtr_options()}]{{',
        person.to_gtr('g', True),
        _parent_node_body(
            person,
            include_siblings,
            include_ancestor_siblings,
            max(-1, max_generations - 1),
        ),
        '}',
    ]
    return ''.join(parts)


def _parent_node_body(
    person: Person,
    include_siblings: bool,
    include_ancestor_siblings: bool,
    max_generations: int,
) -> str:
    parts = []
    if person.child_family and max_generations != 0:
        for parent in person.child_family.parents:
            parts.append(_parent_node(
                parent,
                include_ancestor_siblings,  # After the first level
                                            # there is no difference
                                            # between siblings and
                                            # ancestor siblings
                include_ancestor_siblings,
                max_generations,
            ))
        if include_siblings:
            for child in person.child_family.children:
                if child != person:
                    parts.append(child.to_gtr('c', True))
    return ''.join(parts)


def sandclock(
    person: Person,
    include_siblings: bool = True,
    include_ancestor_siblings: bool = True,
    max_ancestor_generations: int = -1,
    max_descendant_generations: int = -1,
) -> str:
    options = ''
    if person.child_family:
        options = person.child_family.make_gtr_options()
    if options:
        options = f'[{options}]'
    return ''.join([
        f'sandclock{options}{{',
        _child_node(person, max_descendant_generations),
        _parent_node_body(
            person,
            include_siblings,
            include_ancestor_siblings,
            max_ancestor_generations,
        ),
        '}',
    ])


def _validate_limit(ctx, param, value):
    if value < -1:
        raise click.BadParameter('must be >= -1')
    return value


@click.command()
@click.option(
    '--siblings/--no-siblings',
    default=True,
    help='Whether to show the siblings of the target person',
    show_default=True,
)
@click.option(
    '--ancestor-siblings/--no-ancestor-siblings',
    default=True,
    help='Whether to show the siblings of the target person\'s ancestors',
    show_default=True,
)
@click.option(
    '--max-ancestor-generations',
    default=-1,
    type=int,
    metavar='LIMIT',
    callback=_validate_limit,
    help=(
        'Maximum number of ancestor generations to show. Set to -1 for no '
        'limit.'
    ),
    show_default=True,
)
@click.option(
    '--max-descendant-generations',
    default=-1,
    type=int,
    metavar='LIMIT',
    callback=_validate_limit,
    help=(
        'Maximum number of descendant generations to show. Set to -1 for no '
        'limit.'
    ),
    show_default=True,
)
@click.option(
    '--dynamic-generation-limits/--static-generation-limits',
    default=False,
    help=(
        'Whether to adjust the generation limits dynamically when the target '
        'person has less ancestor/descendant generations than the limit. For '
        'example, if --max-ancestor-generations and '
        '--max-descendant-generations are both set to 3 and the target person '
        'has only 1 descendant generation, then --max-ancestor-generations is '
        'increased by 2 if --dynamic-generation-limits is given.'
    ),
    show_default=True,
)
@click.option('-v', '--verbose', count=True, help='Increase verbosity')
@click.argument('gedcom_file', type=click.File('rb'))
@click.argument('xref_id', type=str)
@click.argument(
    'output_file',
    type=click.File('w', encoding='utf-8'),
    default='-',
)
def main(
    siblings: bool,
    ancestor_siblings: bool,
    max_ancestor_generations: int,
    max_descendant_generations: int,
    dynamic_generation_limits: bool,
    verbose: int,
    gedcom_file: BinaryIO,
    xref_id: str,
    output_file: TextIO,
):
    """
    Create databases for genealogytree from GEDCOM files.

    The LaTeX genealogytree package (GTR) provides tools for including
    genealogy trees in LaTeX documents. One way of doing that is by
    storing the genealogical information in a GTR-specific database
    file. This tool allows you to create such databases from GEDCOM
    files (GEDCOM is a popular file format for storing genealogical
    information).

    The input file (GEDCOM_FILE, use "-" for STDIN) is read, and a GTR
    database is written to OUTPUT_FILE (usually has a ".graph"
    extension, defaults to STDOUT). The GTR database contains a
    "sandclock" node for the person with the given GEDCOM XREF-ID.

    The database file can then be used in LaTeX as follows:

    \b
        \\documentclass{article}
        \\usepackage[utf8]{inputenc}
        \\usepackage[all]{genealogytree}
        \\begin{document}
            \\begin{genealogypicture}[template=database pole]
                input{my-database.graph}  % Change filename accordingly
            \\end{genealogypicture}
        \\end{document}
    """
    log.addHandler(logging.StreamHandler())
    if verbose > 1:
        log.setLevel(logging.DEBUG)
    elif verbose > 0:
        log.setLevel(logging.INFO)

    def error(s: str):
        if verbose > 1:
            logging.exception(s)
            sys.exit(1)
        sys.exit(s)

    try:
        persons, families = load_gedcom(gedcom_file)
    except Exception as e:
        error(f'Could not load GEDCOM data: {e}')

    try:
        person = persons[xref_id.replace('@', '')]
    except KeyError:
        error(f'No person with XREF-ID "{xref_id}"')

    if dynamic_generation_limits:
        num_ancestor_generations = person.count_ancestor_generations()
        log.debug(f'{num_ancestor_generations} ancestor generations')
        num_descendant_generations = person.count_descendant_generations()
        log.debug(f'{num_descendant_generations} descendant generations')

        if (
            (num_ancestor_generations > max_ancestor_generations)
            ==  (num_descendant_generations > max_descendant_generations)
        ):
            # Limit is broken in neither direction or in both directions
            pass
        elif num_ancestor_generations > max_ancestor_generations:
            remaining = max_descendant_generations - num_descendant_generations
            if remaining:
                log.debug(
                    f'Dynamically increasing max_ancestor_gerations by '
                    f'{remaining}'
                )
                max_ancestor_generations += remaining
        else:  # num_descendant_generations > max_descendant_generations
            remaining = max_ancestor_generations - num_ancestor_generations
            if remaining:
                log.debug(
                    f'Dynamically increasing max_descendant_gerations by '
                    f'{remaining}'
                )
                max_descendant_generations += remaining

    output_file.write(sandclock(
        person,
        siblings,
        ancestor_siblings,
        max_ancestor_generations,
        max_descendant_generations,
    ))


if __name__ == '__main__':
    main()
