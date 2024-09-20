#!/usr/bin/env python3
# Copyright (c) 2023-2024, ARM Limited.
# SPDX-License-Identifier: Apache-2.0
import os
import re
from functools import cmp_to_key

import compliance_data_exporter
import tosa


def compare_profiles(a, b):
    if a.profiles[0] == b.profiles[0]:
        return 1 if a.mode > b.mode else -1
    if "EXT-" in a.profiles[0]:
        if "EXT-" in b.profiles[0]:
            return 1 if a.profiles[0] > b.profiles[0] else -1
        else:
            return 1
    if "EXT-" in b.profiles[0]:
        return -1
    return 1 if a.profiles[0] > b.profiles[0] else -1


class TOSASpecAsciidocGenerator:
    def __init__(self, spec):
        self.spec = spec

    def generate_enum(self, enum, file):
        file.write(f"\n=== {enum.name}\n")
        file.write(f"{enum.description}\n")
        file.write("|===\n")
        file.write("|Name|Value|Description\n\n")
        for val in enum.values:
            file.write(f"|{val[0]}|{val[1]}|{val[2]}\n")
        file.write("|===\n")

    def generate_operator(self, op, file):
        has_ctc = False
        file.write("\n*Arguments:*\n")
        file.write("[cols='3,3,2,2,4,8']")
        file.write("\n|===\n")
        file.write("|Argument|Type|Name|Shape|Rank|Description\n\n")
        for arg in op.arguments:
            # Argument
            cats = arg.categories
            if len(cats) > 1:
                cattext = ""
                sep = ""
                for cat in cats:
                    proflist = "/".join(cat.profiles)
                    profcaption = "profiles" if len(cat.profiles) > 1 else "profile"
                    cattext += sep + cat.name.title() + f" ({proflist} {profcaption})"
                    sep = " "
            else:
                cattext = cats[0].name.title()

            if arg.ctc:
                has_ctc = True

            # Type
            if arg.type == "tensor_t":
                if (
                    arg.categories[0].name == "attribute"
                    and len(arg.rank) == 2
                    and arg.rank[0] == arg.rank[1] == "0"
                ):
                    argtype = f"{arg.tensor_element_type}"
                else:
                    argtype = f"T<{arg.tensor_element_type}>"
            elif arg.type == "tensor_list_t":
                if arg.tensor_element_type == "-":
                    argtype = "tensor_list_t"
                else:
                    argtype = f"tensor_list_t<T<{arg.tensor_element_type}>>"
            elif arg.type == "shape_t":
                if arg.shape != "-":
                    argtype = f"shape_t<{arg.shape}>"
                else:
                    argtype = "shape_t<>"
            else:
                argtype = arg.type

            # Rank
            if len(arg.rank) > 0:
                if arg.rank[0] == arg.rank[1]:
                    rank = f"{arg.rank[0]}"
                else:
                    rank = f"{arg.rank[0]} to {arg.rank[1]}"
            else:
                rank = ""

            # Format and write line
            file.write(
                f"|{cattext}|{argtype}|{arg.name}|{arg.shape}"
                f"|{rank}|{arg.description}\n"
            )

        file.write("|===\n")

        if has_ctc:
            file.write("\n*Compile Time Constant Status:*\n\n")
            file.write("|===\n")
            file.write("|Argument|CTC enabled profile(s)|CTC disabled extension(s)\n\n")
            for arg in op.arguments:
                if len(arg.ctc) > 0:
                    file.write(f"|{arg.name}|{', '.join(arg.ctc)}|")
                if len(arg.ctc_remove) > 0:
                    file.write(f"{', '.join(arg.ctc_remove)}")
                file.write("\n")
            file.write("|===\n")

        if op.typesupports:
            file.write("\n*Supported Data Types:*\n\n")
            file.write("|===\n")
            header = "|Profile/Extension|Mode"
            for ty in op.types:
                header += f"|{ty}"
            file.write(header)
            file.write("\n\n")
            for tysup in sorted(op.typesupports, key=cmp_to_key(compare_profiles)):
                profile = " or ".join(tysup.profiles) if tysup.profiles else "Any"
                entry = f"|{profile}|{tysup.mode}"
                for ty in op.types:
                    entry += f"|{tysup.tymap[ty]}"
                entry += "\n"
                file.write(entry)
            file.write("|===\n")
        file.write("\n*Operation Function:*\n\n")
        leveltext = ""
        for arg in op.arguments:
            if len(arg.levellimits) > 0:
                for limit in arg.levellimits:
                    leveltext += "LEVEL_CHECK(" + limit[0] + " <= " + limit[1] + ");\n"
        if len(leveltext) > 0:
            file.write(f"[source,c++]\n----\n{leveltext}\n----\n")

    def generate(self, outdir):
        os.makedirs(outdir, exist_ok=True)

        # Generate version information
        major = self.spec.version_major
        minor = self.spec.version_minor
        patch = self.spec.version_patch
        with open(os.path.join(outdir, "version.adoc"), "w") as f:
            f.write(":tosa-version-string: {}.{}.{}".format(major, minor, patch))
            if self.spec.version_is_draft:
                f.write(" draft")
            f.write("\n")

        # Generate profile table
        with open(os.path.join(outdir, "profiles.adoc"), "w") as f:
            f.write("|===\n")
            f.write("|Profile|Name|Description|Specification Status\n\n")
            for profile in self.spec.profiles:
                f.write(
                    f"|{profile.profile}|{profile.name}|"
                    f"{profile.description}|{profile.status}\n"
                )
            f.write("|===\n")

        # Generate profile table
        with open(os.path.join(outdir, "profile_extensions.adoc"), "w") as f:
            f.write("|===\n")
            f.write("|Name|Description|Allowed profiles|Specification Status\n\n")
            for profile_extension in self.spec.profile_extensions:
                f.write(
                    f"|{profile_extension.name}|{profile_extension.description}"
                    f"|{','.join(profile_extension.profiles)}"
                    f"|{profile_extension.status}\n"
                )
            f.write("|===\n")

        # Generate level maximums table
        with open(os.path.join(outdir, "levels.adoc"), "w") as f:
            f.write("|===\n")
            f.write("|tosa_level_t")
            for level in self.spec.levels:
                f.write("|tosa_level_{}".format(level.name))
            f.write("\n")
            f.write("|Description")
            for level in self.spec.levels:
                f.write("|{}".format(level.desc))
            f.write("\n")
            for param in self.spec.levels[0].maximums:
                f.write("|{}".format(param))
                for level in self.spec.levels:
                    f.write("|{}".format(level.maximums[param]))
                f.write("\n")
            f.write("|===\n")

        # Generator operators
        opdir = os.path.join(outdir, "operators")
        os.makedirs(opdir, exist_ok=True)
        for group in self.spec.operatorgroups:
            for op in group.operators:
                with open(os.path.join(opdir, op.name + ".adoc"), "w") as f:
                    self.generate_operator(op, f)
        with open(os.path.join(outdir, "enums.adoc"), "w") as f:
            for enum in self.spec.enums:
                self.generate_enum(enum, f)

        all_operators = []
        for group in self.spec.operatorgroups:
            for op in group.operators:
                all_operators.append(op)

        # Generate profile operator appendix
        with open(os.path.join(outdir, "profile_ops.adoc"), "w") as f:
            f.write("=== Profiles\n")
            for profile in self.spec.profiles:
                f.write(f"==== {profile.profile}\n")
                f.write(f"{profile.description}\n\n")
                f.write(f"Status: {profile.status}\n")
                f.write("|===\n")
                f.write("|Operator|Mode|Version Added\n\n")
                for op in sorted(all_operators, key=lambda o: o.name):
                    if op.typesupports:
                        for tysup in op.typesupports:
                            if profile.name in tysup.profiles:
                                f.write(
                                    f"|{op.name}|{tysup.mode}|{tysup.version_added}\n"
                                )
                f.write("|===\n")

            f.write("=== Profile Extensions\n")
            for pext in self.spec.profile_extensions:
                f.write(f"==== {pext.name} extension\n")
                f.write(f"{pext.description}\n\n")
                f.write(f"Status: {pext.status}\n\n")
                f.write(f"Compatible profiles: {', '.join(pext.profiles)}\n\n")
                f.write("|===\n")
                f.write("|Operator|Mode|Version Added|Note\n\n")
                for op in sorted(all_operators, key=lambda o: o.name):
                    if op.typesupports:
                        for tysup in op.typesupports:
                            for profile in tysup.profiles:
                                if profile.find(pext.name) != -1:
                                    note = ""
                                    m = re.match(r"(.*) and (.*)", profile)
                                    if m:
                                        if m[1] == pext.name:
                                            note = f"If {m[2]} is also supported"
                                        else:
                                            note = f"If {m[1]} is also supported"
                                    f.write(
                                        f"|{op.name}|{tysup.mode}|"
                                        f"{tysup.version_added}|{note}\n"
                                    )
                    for arg in op.arguments:
                        if pext.name in arg.ctc_remove:
                            f.write(f"|{op.name}|all||Remove CTC from {arg.name}\n")
                f.write("|===\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--xml", required=True, help="Path to specification XML")
    parser.add_argument("--outdir", required=True, help="Output directory")
    parser.add_argument(
        "--profile",
        required=False,
        action="store_true",
        help="Export the profile compliance data to the location indicated by --outdir",
    )
    args = parser.parse_args()

    try:
        spec = tosa.TOSASpec(args.xml)
        if args.profile:
            compliance_data_exporter.print_profiles_extensions(spec, args.outdir)
    except RuntimeError as e:
        print(f"Failure reading/validating XML spec: {str(e)}")
        exit(1)

    generator = TOSASpecAsciidocGenerator(spec)
    generator.generate(args.outdir)
