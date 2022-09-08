#
# This confidential and proprietary software may be used only as
# authorised by a licensing agreement from ARM Limited
# (C) COPYRIGHT 2020-2022 ARM Limited
# ALL RIGHTS RESERVED
# The entire notice above must be reproduced on all authorised
# copies and copies may only be made to the extent permitted
# by a licensing agreement from ARM Limited.
#

TOSAREVISION=0.41.0 draft
MKDIR=mkdir -p
ASCIIDOC=asciidoctor
ASPELL=aspell
SHELL=/bin/bash -o pipefail
XMLLINT = xmllint

HTMLDIR=out/html
PDFDIR=out/pdf
GENDIR=out/gen

COMMON_ARGS= -a revnumber="$(TOSAREVISION)" -a generated="$(abspath $(GENDIR))"

SPECSRC := tosa_spec.adoc
ADOCFILES = $(wildcard chapters/[A-Za-z]*.adoc) $(wildcard $(GENDIR)/*/*.adoc)
SPECFILES = $(ADOCFILES) tosa.css
FIGURES = $(wildcard figures/*.svg)
SPECXML := tosa.xml
SPECSCHEMA := tosa.xsd
GENSCRIPTS := tools/tosa.py tools/genspec.py

GEN := $(GENDIR)/gen.stamp

.DELETE_ON_ERROR:

.PHONY: all html pdf clean spell copy_html_figures lint

all: spell html pdf

html: lint copy_html_figures $(HTMLDIR)/tosa_spec.html

pdf: lint $(PDFDIR)/tosa_spec.pdf

clean:
	$(RM) $(HTMLDIR)/tosa_spec.html
	$(RM) -rf $(HTMLDIR)/figures
	$(RM) $(PDFDIR)/tosa_spec.pdf
	$(RM) -r $(GENDIR)
	$(RM) out/lint.txt

lint: out/lint.txt

spell: out/spell.txt

copy_html_figures: $(FIGURES)
	$(MKDIR) -p $(HTMLDIR)/figures
	cp $(FIGURES) $(HTMLDIR)/figures

.PRECIOUS: out/spell.txt
out/spell.txt: $(ADOCFILES) FORCE
	@echo Running spell check
	@mkdir -p $(@D)
	@tools/get_descriptions.py $(ADOCFILES) \
		| $(ASPELL) list -v -l en-US --encoding=UTF-8 --add-extra-dicts=./tools/dictionary.dic\
		| sort -u > $@
	@if [ -s $@ ] ; then \
		echo Spelling errors detected, check $@; exit 1; \
		else echo No spelling errors found ; \
	fi

.PRECIOUS: out/lint.txt
out/lint.txt: $(SPECXML) $(SPECSCHEMA)
	echo Linting XML
	$(XMLLINT) --noout --schema $(SPECSCHEMA) $(SPECXML)

$(GEN): $(SPECXML) $(GENSCRIPTS)
	tools/genspec.py --xml $(SPECXML) --outdir $(GENDIR)
	@touch $@

$(HTMLDIR)/tosa_spec.html: $(SPECSRC) $(SPECFILES) $(GEN)
	$(MKDIR) $(HTMLDIR)
	$(ASCIIDOC) -b html5 -a stylesheet=tosa.css $(COMMON_ARGS) -o $@ $<

$(PDFDIR)/tosa_spec.pdf: $(SPECSRC) $(SPECFILES) $(GEN)
	$(MKDIR) $(PDFDIR)
	$(ASCIIDOC) -r asciidoctor-pdf -b pdf $(COMMON_ARGS) -o $@ $(SPECSRC)

.PHONY: FORCE
FORCE:
