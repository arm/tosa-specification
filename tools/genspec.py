#!/usr/bin/env python3
import os

import tosa

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
        file.write("\n*Arguments:*\n")
        file.write("[cols='2,1,1,1,2,4']")
        file.write("\n|===\n")
        file.write("|Argument|Type|Name|Shape|Rank|Description\n\n")
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
            if len(arg.rank) > 0:
                if (arg.rank[0] == arg.rank[1]):
                    rank = f'{arg.rank[0]}'
                else:
                    rank = f'{arg.rank[0]} to {arg.rank[1]}'
            else:
                rank = ""
            file.write(
                f"|{cattext}|{arg.type}|{arg.name}|{arg.shape}|{rank}|{arg.description}\n"
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
                   leveltext += "LEVEL_CHECK(" + limit[0] + " <= " + limit[1] + ");\n"
        if (len(leveltext) > 0):
            file.write(f"[source,c++]\n----\n{leveltext}\n----\n")

    def generate(self, outdir):
        os.makedirs(outdir, exist_ok=True)

        # Generate version information
        major = self.spec.version_major
        minor = self.spec.version_minor
        patch = self.spec.version_patch
        with open(os.path.join(outdir, "version.adoc"), 'w') as f:
            f.write(':tosa-version-string: {}.{}.{}'.format(major, minor, patch))
            if self.spec.version_is_draft:
                f.write(' draft')
            f.write('\n')

        # Generate level maximums table
        with open(os.path.join(outdir, "levels.adoc"), 'w') as f:
            f.write('|===\n')
            f.write('|tosa_level_t')
            for level in self.spec.levels:
                f.write('|tosa_level_{}'.format(level.name))
            f.write('\n')
            f.write('|Description')
            for level in self.spec.levels:
                f.write('|{}'.format(level.desc))
            f.write('\n')
            for param in self.spec.levels[0].maximums:
                f.write('|{}'.format(param))
                for level in self.spec.levels:
                    f.write('|{}'.format(level.maximums[param]))
                f.write('\n')
            f.write('|===\n')

        # Generator operators
        opdir = os.path.join(outdir, "operators")
        os.makedirs(opdir, exist_ok=True)
        for group in self.spec.operatorgroups:
            for op in group.operators:
                with open(os.path.join(opdir, op.name + ".adoc"), "w") as f:
                    self.generate_operator(op, f)
        with open(os.path.join(outdir, "enums.adoc"), 'w') as f:
            for enum in self.spec.enums:
                self.generate_enum(enum, f)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--xml", required=True, help="Path to specification XML")
    parser.add_argument("--outdir", required=True, help="Output directory")
    args = parser.parse_args()

    try:
        spec = tosa.TOSASpec(args.xml)
    except RuntimeError as e:
        print(f"Failure reading/validating XML spec: {str(e)}")
        exit(1)

    generator = TOSASpecAsciidocGenerator(spec)
    generator.generate(args.outdir)
