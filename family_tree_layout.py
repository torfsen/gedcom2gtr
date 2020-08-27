#!/usr/bin/env python

from dataclasses import dataclass
import datetime as dt
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ged4py.date import DateValue, DateValueVisitor
from ged4py.model import Individual
from ged4py.parser import GedcomReader

MONTH_NAME_TO_NUMBER = {
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


class DateFormatter(DateValueVisitor):
    """
    Visitor class that produces string representation of dates.
    """
    def visitSimple(self, date):
        return f'{self._format_date(date.date)}'

    def visitPeriod(self, date):
        return f'from {self._format_date(date.date1)} to {self._format_date(date.date2)}'

    def visitFrom(self, date):
        return f'from {self._format_date(date.date)}'

    def visitTo(self, date):
        return f'to {self._format_date(date.date)}'

    def visitRange(self, date):
        return f'between {self._format_date(date.date1)} and {self._format_date(date.date2)}'

    def visitBefore(self, date):
        return f'before {self._format_date(date.date)}'

    def visitAfter(self, date):
        return f'after {self._format_date(date.date)}'

    def visitAbout(self, date):
        return f'about {self._format_date(date.date)}'

    def visitCalculated(self, date):
        return f'calculated {self._format_date(date.date)}'

    def visitEstimated(self, date):
        return f'estimated {self._format_date(date.date)}'

    def visitInterpreted(self, date):
        return f'interpreted {self._format_date(date.date)} ({date.phrase})'

    def visitPhrase(self, date):
        return f'({date.phrase})'

    def format(self, date_value) -> str:
        return date_value.accept(self)

    def _format_date(self, date) -> str:
        if date.day:
            return f'{date.year}-{MONTH_NAME_TO_NUMBER[date.month]:02d}-{date.day:02d}'
        elif date.month:
            return f'{date.year}-{MONTH_NAME_TO_NUMBER[date.month]:02d}'
        return str(date.year)


date_formatter = DateFormatter()


class Sex(Enum):
    FEMALE = 'F'
    MALE = 'M'


@dataclass
class Name:
    given: Optional[str]
    last: Optional[str]

    def __str__(self):
        given = self.given or '?'
        last = self.last or '?'
        return f'{given} {last}'


@dataclass
class Person:
    names: Dict[str, Name]
    sex: Optional[Sex]
    father: Optional['Person']
    mother: Optional['Person']
    birth_date: Optional[DateValue]
    death_date: Optional[DateValue]

    def get_names(self) -> Tuple[Optional[Name], Optional[Name]]:
        default_name = self.names.get(None)
        married_name = self.names.get('married')
        maiden_name = self.names.get('maiden') or self.names.get('birth')

        if default_name and married_name and not maiden_name:
            # Assume default name is maiden name
            maiden_name = default_name
            default_name = None
        elif default_name and maiden_name and not married_name:
            # Assume default name is married name
            married_name = default_name
            default_name = None

        if default_name:
            # A default name and both a married and maiden name, or a
            # default name and neither a married nor a maiden name. This
            # is hard to interpret correctly automatically, so we just
            # return the default name.
            return default_name, None

        if married_name and maiden_name:
            if married_name != maiden_name:
                return married_name, maiden_name
            return married_name, None

        return (married_name or maiden_name), None

    def __str__(self):
        default_name, maiden_name = self.get_names()
        if not default_name:
            return '?'
        name_parts = [str(default_name)]
        if maiden_name:
            name_parts.append(f'({maiden_name.last})')
        return ' '.join(name_parts)


@dataclass
class Family:
    spouses: List[Person]
    children: List[Person]
    marriage_date: Optional[DateValue]


def load_gedcom(fn: Path) -> Tuple[List[Person], List[Family]]:
    # ged4py 0.2.2 has problems with hashing, see
    # https://github.com/andy-z/ged4py/issues/22
    # Our workaround is to use the xref_id instead.
    indi_to_person = {}
    families = []
    with GedcomReader(fn) as reader:
        # First pass, create persons
        for indi in reader.records0('INDI'):
            print(indi)

            names = {
                name_record.type: Name(*name_record.value[:2])
                for name_record in indi.sub_tags('NAME')
            }
            #print(names)

            birth_date = indi.sub_tag_value('BIRT/DATE')
            #birth_date_str = date_formatter.format(birth_date) if birth_date else None
            #print(birth_date_str)

            death_date = indi.sub_tag_value('DEAT/DATE')
            #death_date_str = date_formatter.format(death_date) if death_date else None
            #print(death_date_str)

            sex_str = indi.sub_tag_value('SEX')
            sex = Sex(sex_str) if sex_str else None
            #print(sex)

            person = Person(
                names,
                sex,
                None,  # Father will be filled in later on
                None,  # Mother will be filled in later on
                birth_date,
                death_date,
            )
            indi_to_person[indi.xref_id] = person

            print(person)
            #print(p.get_names())

            print()

        print()
        print('***')
        print()

        # Second pass, set parents
        for indi in reader.records0('INDI'):
            person = indi_to_person[indi.xref_id]
            if indi.father:
                person.father = indi_to_person[indi.father.xref_id]
                print(f'{person.father} is the father of {person}')
            if indi.mother:
                person.mother = indi_to_person[indi.mother.xref_id]
                print(f'{person.mother} is the mother of {person}')

        print()
        print('***')
        print()

        # Third pass, create families
        for fam in reader.records0('FAM'):
            print(fam)
            spouses = []
            for tag in ['HUSB', 'WIFE']:
                spouse = fam.sub_tag(tag)
                if spouse:
                    spouses.append(indi_to_person[spouse.xref_id])
            children = [
                indi_to_person[child.xref_id]
                for child in fam.sub_tags('CHIL')
            ]

            # TODO: Marriage date
            marriage_date = None

            families.append(Family(
                spouses,
                children,
                marriage_date,
            ))

            print()

    return list(indi_to_person.values()), families


if __name__ == '__main__':
    import sys
    load_gedcom(sys.argv[1])
