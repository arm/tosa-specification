#
# This confidential and proprietary software may be used only as
# authorised by a licensing agreement from ARM Limited
# (C) COPYRIGHT 2020-2022 ARM Limited
# ALL RIGHTS RESERVED
# The entire notice above must be reproduced on all authorised
# copies and copies may only be made to the extent permitted
# by a licensing agreement from ARM Limited.
#

TOSAREVISION=0.24.0 draft
MKDIR=mkdir -p
ASCIIDOC=asciidoctor
ASPELL=aspell

HTMLDIR=out/html
PDFDIR=out/pdf

COMMON_ARGS= -a revnumber="$(TOSAREVISION)"

SPECSRC := tosa_spec.adoc
ADOCFILES = $(wildcard chapters/[A-Za-z]*.adoc)
SPECFILES = $(ADOCFILES) tosa.css

.DELETE_ON_ERROR:

.PHONY: all html pdf clean spell

all: spell html pdf

html: $(HTMLDIR)/tosa_spec.html

pdf: $(PDFDIR)/tosa_spec.pdf

clean:
	$(RM) $(HTMLDIR)/tosa_spec.html
	$(RM) $(PDFDIR)/tosa_spec.pdf

spell: out/spell.txt

out/spell.txt: $(ADOCFILES) FORCE
	@echo Running spell check
	@mkdir -p $(@D)
	@tools/get_descriptions.py $(ADOCFILES) \
		| $(ASPELL) list -v -l en-US --encoding=UTF-8 --add-extra-dicts=./tools/dictionary.dic\
		| sort -u > $@
	@-if [ -s $@ ] ; then \
		echo Spelling errors detected, check $@; \
		else echo No spelling errors found ; \
	fi

$(HTMLDIR)/tosa_spec.html: $(SPECSRC) $(SPECFILES)
	$(MKDIR) $(HTMLDIR)
	$(ASCIIDOC) -b html5 -a stylesheet=tosa.css $(COMMON_ARGS) -o $@ $<

$(PDFDIR)/tosa_spec.pdf: $(SPECSRC) $(SPECFILES)
	$(MKDIR) $(PDFDIR)
	$(ASCIIDOC) -r asciidoctor-pdf -b pdf $(COMMON_ARGS) -o $@ $(SPECSRC)

.PHONY: FORCE
FORCE:
