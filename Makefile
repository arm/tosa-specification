#
# This confidential and proprietary software may be used only as
# authorised by a licensing agreement from ARM Limited
# (C) COPYRIGHT 2020 ARM Limited
# ALL RIGHTS RESERVED
# The entire notice above must be reproduced on all authorised
# copies and copies may only be made to the extent permitted
# by a licensing agreement from ARM Limited.
#

TOSAREVISION=0.23.0
MKDIR=mkdir -p
ASCIIDOC=asciidoctor

HTMLDIR=out/html
PDFDIR=out/pdf

COMMON_ARGS= -a revnumber="$(TOSAREVISION)"

SPECSRC := tosa_spec.adoc
SPECFILES = $(wildcard chapters/[A-Za-z]*.adoc) tosa.css

.DELETE_ON_ERROR:

.PHONY: all html pdf clean

all: html pdf

html: $(HTMLDIR)/tosa_spec.html

pdf: $(PDFDIR)/tosa_spec.pdf

clean:
	$(RM) $(HTMLDIR)/tosa_spec.html
	$(RM) $(PDFDIR)/tosa_spec.pdf

$(HTMLDIR)/tosa_spec.html: $(SPECSRC) $(SPECFILES)
	$(MKDIR) $(HTMLDIR)
	$(ASCIIDOC) -b html5 -a stylesheet=tosa.css $(COMMON_ARGS) -o $@ $<

$(PDFDIR)/tosa_spec.pdf: $(SPECSRC) $(SPECFILES)
	$(MKDIR) $(PDFDIR)
	$(ASCIIDOC) -r asciidoctor-pdf -b pdf $(COMMON_ARGS) -o $@ $(SPECSRC)
