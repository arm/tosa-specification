TOSA Specification Repository
=============

This repository contains the source files for the TOSA specification.
See the specification itself for details on the purpose and definition
of the specification.

# Build requirements
The TOSA specification is written in asciidoc format, and has been built
using the following tools:

* Asciidoctor 1.5.5 or later ([Asciidoctor](https://asciidoctor.org))
* Asciidoctor-pdf
* GNU Make 4.1 or later

The default `make` build creates both an html and a pdf version of the specification
in out/html and out/pdf

If only an html build is required, `make html` will build only the html file,
and asciidoctor-pdf is not needed.

If only a pdf build is required, `make pdf` will build only the pdf.