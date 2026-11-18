<!--
PDX-FileCopyrightText: Copyright 2020,2022,2024,2026 Arm Limited and/or its affiliates.
SPDX-License-Identifier: Apache-2.0
-->

TOSA Specification Repository
=============

This repository contains the source files for the TOSA specification.
See the specification itself for details on the purpose and definition
of the specification.

# Pre-rendered versions

Rendered versions of the TOSA specification in HTML format.

Releases:
- `v1.1.0` - https://arm.github.io/tosa-specification/releases/v1.1.0/
- `v1.0.2` - https://arm.github.io/tosa-specification/releases/v1.0.2/
- `v1.0.1` - https://arm.github.io/tosa-specification/releases/v1.0.1/
- `v1.0.0` - https://arm.github.io/tosa-specification/releases/v1.0.0/

In development:
- `main` - https://arm.github.io/tosa-specification/

# Build requirements
The TOSA specification is written in asciidoc format, and has been built
using the following tools:

* Asciidoctor 1.5.5 or later ([Asciidoctor](https://asciidoctor.org))
* Asciidoctor-pdf
* GNU Make 4.1 or later
* xmllint
* Python 3.8 or later

The default `make` build creates both an html and a pdf version of the specification
in out/html and out/pdf

If only an html build is required, `make html` will build only the html file,
and asciidoctor-pdf is not needed.

If only a pdf build is required, `make pdf` will build only the pdf.

# Pre Commit Checks

Before pushing a commit, pre commit checks must be run to ensure conformity.

## Prerequisites
* pre-commit (tested with 3.8.0)

Install with:

``` bash
pip install pre-commit==3.8.0
```

## Run Pre Commit Checks

``` bash
pre-commit run --all
```
