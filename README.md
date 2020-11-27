# gedcom2gtr

*Convert [GEDCOM] files into databases for the [genealogytree] LaTeX package*


## Installation

*gedcom2gtr* can be installed via [pip]:

    pip install git+https://github.com/torfsen/gedcom2gtr.git@v0.1.0


## Usage

```none
$ gedcom2gtr --help
Usage: gedcom2gtr [OPTIONS] GEDCOM_FILE XREF_ID [OUTPUT_FILE]

  Create databases for genealogytree from GEDCOM files.

  The LaTeX genealogytree package (GTR) provides tools for including
  genealogy trees in LaTeX documents. One way of doing that is by storing
  the genealogical information in a GTR-specific database file. This tool
  allows you to create such databases from GEDCOM files (GEDCOM is a popular
  file format for storing genealogical information).

  The input file (GEDCOM_FILE, use "-" for STDIN) is read, and a GTR
  database is written to OUTPUT_FILE (usually has a ".graph" extension,
  defaults to STDOUT). The GTR database contains a "sandclock" node for the
  person with the given GEDCOM XREF-ID.

  The database file can then be used in LaTeX as follows:

      \documentclass{article}
      \usepackage[utf8]{inputenc}
      \usepackage[all]{genealogytree}
      \begin{document}
          \begin{genealogypicture}[template=database pole]
              input{my-database.graph}  % Change filename accordingly
          \end{genealogypicture}
      \end{document}

Options:
  --siblings / --no-siblings      Whether to show the siblings of the target
                                  person  [default: True]

  --ancestor-siblings / --no-ancestor-siblings
                                  Whether to show the siblings of the target
                                  person's ancestors  [default: True]

  --max-ancestor-generations LIMIT
                                  Maximum number of ancestor generations to
                                  show. Set to -1 for no limit.  [default: -1]

  --max-descendant-generations LIMIT
                                  Maximum number of descendant generations to
                                  show. Set to -1 for no limit.  [default: -1]

  --dynamic-generation-limits / --static-generation-limits
                                  Whether to adjust the generation limits
                                  dynamically when the target person has less
                                  ancestor/descendant generations than the
                                  limit. For example, if --max-ancestor-
                                  generations and --max-descendant-generations
                                  are both set to 3 and the target person has
                                  only 1 descendant generation, then --max-
                                  ancestor-generations is increased by 2 if
                                  --dynamic-generation-limits is given.
                                  [default: False]

  -v, --verbose                   Increase verbosity
  --help                          Show this message and exit.
```

## History

See the file `CHANGELOG.md`.


## Development

First clone the repository, then install the development dependencies (runtime and development dependencies are managed via [pip-tools]):

```shell
pip install -r dev-requirements.txt
```

You can run the [pre-commit] checks via

```shell
make pre-commit
```

and tests via

```shell
make tests
```

A test coverage report is automatically stored in `htmlcov`.

Package versions are managed via [versioneer].


## License

Copyright (c) 2020, [Florian Brucker](www.florianbrucker.de). Released under the MIT license. See the file `LICENSE` for details.


[GEDCOM]: https://en.wikipedia.org/wiki/GEDCOM
[genealogytree]: https://www.ctan.org/pkg/genealogytree
[pip]: https://pip.pypa.io/en/stable/
[pip-tools]: https://github.com/jazzband/pip-tools
[pre-commit]: https://pre-commit.com/
[versioneer]: https://github.com/python-versioneer/python-versioneer
