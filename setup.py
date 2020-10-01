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

from pathlib import Path
import re

from setuptools import setup


HERE = Path(__file__).parent.resolve()
SOURCE_FILE = HERE / 'gedcom2gtr' / '__init__.py'

version = None
in_doc_str = False
doc_lines = []
with SOURCE_FILE.open(encoding='utf8') as f:
    for line in f:
        s = line.strip()
        m = re.match(r"""__version__\s*=\s*['"](.*)['"]""", line)
        if m:
            version = m.groups()[0]
        elif s in ['"""', "'''"]:
            if in_doc_str:
                in_doc_str = False
            elif not doc_lines:
                in_doc_str = True
        elif in_doc_str:
            doc_lines.append(line)

if not version:
    raise RuntimeError(f'Could not extract version from "{SOURCE_FILE}"')
if not doc_lines:
    raise RuntimeError(f'Could not extract doc string from "{SOURCE_FILE}"')

with (HERE / 'requirements.txt').open() as f:
    requirements = f.readlines()


setup(
    name='gedcom2gtr',
    description='Convert GEDCOM files to genealogytree databases',
    long_description='\n'.join(doc_lines),
    version=version,
    license='MIT',
    keywords='gedcom latex genealogytree genealogy'.split(),
    classifiers=[
        # See https://pypi.org/pypi?%3Aaction=list_classifiers
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
    ],
    author='Florian Brucker',
    author_email='mail@florianbrucker.de',
    packages=['gedcom2gtr'],
    install_requires=requirements,
    entry_points='''
        [console_scripts]
        gedcom2gtr=gedcom2gtr:main
    ''',
)
