#!/usr/bin/env python

# Copyright (c) 2026 Florian Brucker (www.florianbrucker.de)
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
Utility script to generate a PDF from a `.graph` file.
"""

TEMPLATE = r"""
\documentclass{article}
\usepackage[a0paper]{geometry}
\usepackage[utf8]{inputenc}
\usepackage{lmodern}  % http://ctan.org/pkg/lm
\usepackage[all]{genealogytree}

\gtrset{language=german-german}

\begin{document}
    \begin{genealogypicture}[
        template=database pole,
        database format=short,
        date format=dd.mm.yyyy,
        label options={
            draw,
            rounded corners,
            fill=white,
            node font=\scriptsize\sffamily,
        },
        level distance=1cm,
        level size=2cm,
        show id,
    ]
        input{GRAPH_FN}
    \end{genealogypicture}
\end{document}
"""

if __name__ == "__main__":
    import subprocess
    import sys
    import tempfile
    from pathlib import Path

    if len(sys.argv) not in (2, 3):
        sys.exit(f"Usage: {sys.argv[0]} GRAPH_FILE [PDF_FILE]")
    graph_fn = Path(sys.argv[1]).resolve()
    if len(sys.argv) > 2:
        pdf_fn = Path(sys.argv[2]).resolve()
    else:
        pdf_fn = graph_fn.with_suffix(".pdf")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir).resolve()
        tex_fn = temp_dir / "temp.tex"
        tex_fn.write_text(TEMPLATE.replace("GRAPH_FN", str(graph_fn)))

        subprocess.run(
            ["pdflatex", str(tex_fn)],
            check=True,
            cwd=temp_dir,
        )

        output_fn = temp_dir / "temp.pdf"
        output_fn.rename(pdf_fn)
