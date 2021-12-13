#!/usr/bin/env python3

# Copyright (c) 2022, ARM Limited.
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

# Script to pull the descriptions out of the specification so that
# they can be run through a spellcheck with less noise

import argparse
import re

parser = argparse.ArgumentParser()
parser.add_argument(
    "filenames", nargs="+", help="filename to extract descriptions from"
)
args = parser.parse_args()

for name in args.filenames:
    # special case the license as it is all text
    if name == "chapters/tosa_license.adoc":
        always_in = True
    else:
        always_in = False
    with open(name, "r") as docfile:
        in_description = False
        for text in docfile:
            if always_in:
                print(text)
                continue
            if not in_description:
                # Look for the start of an operator
                if re.match(r'^===', text):
                    in_description = True
                    print(text)
            else:
                # Stop when we get to a subsection like *Arguments*
                # or pseudocode in a [source] section. Spellcheck is
                # not useful there
                if re.match(r'[\[\*]', text):
                    in_description = False
                else:
                    print(text)
