#!/usr/bin/env python3
import os

import tosa


class TOSASpecAsciidocGenerator:
    def __init__(self, spec):
        self.spec = spec

    def generate_operator(self, op, file):
        file.write("\n*Arguments:*\n")
        file.write("\n|===\n")
        file.write("|Argument|Type|Name|Shape|Description\n\n")
        for arg in op.arguments:
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
            file.write(
                f"|{cattext}|{arg.type}|{arg.name}|{arg.shape}|{arg.description}\n"
            )
        file.write("|===\n")
        if op.typesupports:
            file.write("\n*Supported Data Types:*\n\n")
            file.write("|===\n")
            header = "|Profile|Mode"
            for ty in op.types:
                header += f"|{ty}"
            file.write(header)
            file.write("\n\n")
            for tysup in op.typesupports:
                profile = ", ".join(tysup.profiles) if tysup.profiles else "Any"
                entry = f"|{profile}|{tysup.mode}"
                for ty in op.types:
                    entry += f"|{tysup.tymap[ty]}"
                entry += "\n"
                file.write(entry)
            file.write("|===\n")
        file.write("\n*Operation Function:*\n\n")
        leveltext = ""
        for arg in op.arguments:
            if (len(arg.levellimits) > 0):
                for limit in arg.levellimits:
                   leveltext += "    LEVEL_CHECK(" + limit[0] + " <= " + limit[1] + ");\n"
        if (len(leveltext) > 0):
            file.write(
                f"[source,c++]\n----\nif (level != tosa_level_none) {{\n{leveltext}}}\n----\n"
            )

    def generate(self, outdir):
        opdir = os.path.join(outdir, "operators")
        os.makedirs(opdir, exist_ok=True)
        for group in self.spec.operatorgroups:
            for op in group.operators:
                with open(os.path.join(opdir, op.name + ".adoc"), "w") as f:
                    self.generate_operator(op, f)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--xml", required=True, help="Path to specification XML")
    parser.add_argument("--outdir", required=True, help="Output directory")
    args = parser.parse_args()

    spec = tosa.TOSASpec(args.xml)

    generator = TOSASpecAsciidocGenerator(spec)
    generator.generate(args.outdir)
