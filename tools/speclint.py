#!/usr/bin/env python3
# Copyright (c) 2023-2024, ARM Limited.
# SPDX-License-Identifier: Apache-2.0
import tosa


class TOSASpecLinter:
    def __init__(self, spec):
        self.spec = spec
        self.warnings = 0

    def WARN(self, string):
        print(string)
        self.warnings += 1

    def lint_enum(self, enum):
        pass

    def lint_argument(self, operator, arg):
        # Check for an argument in multiple categories. This used to be
        # supported, but is no longer recommended
        if len(arg.categories) > 1:
            self.WARN(
                f"Operator {operator.name} argument {arg.name}"
                " is in multiple categories"
            )
        # Check for a rank 0 tensor attribute. This is now deprecated usage
        if (
            arg.categories[0].name == "attribute"
            and arg.type == "tensor_t"
            and arg.rank[0] == "0"
            and arg.rank[1] == "0"
        ):
            self.WARN(
                f"Operator {operator.name} tensor attribute argument {arg.name}"
                " is always rank 0"
            )

    def lint_typesupport(self, typesupport, op):
        # Check that all types are defined for each typesupport
        # and that there are no extras
        for t in typesupport.tymap:
            if typesupport.tymap[t] is None:
                self.WARN(
                    f"Operator {op.name} mode {typesupport.mode} type {t} not found"
                )
        known_keys = ["mode", "version_added"]
        for k in typesupport.tskeys:
            if k not in known_keys and k not in op.types:
                self.WARN(
                    f"Operator {op.name} mode {typesupport.mode}"
                    f" has an unexpected key {k}"
                )

    def lint_operator(self, op):
        argtypes = ["input", "attribute", "output"]
        current_argtype = 0
        for arg in op.arguments:
            # Arguments should only be in one category
            cats = arg.categories
            if len(cats) > 1:
                self.WARN(
                    f"Operator {op.name} argument in more than one category: {arg.name}"
                )
            i = argtypes.index(cats[0].name)

            # Arguments should be kept as inputs/attributes/outputs
            if i < current_argtype:
                self.WARN(
                    f"Operator {op.name} argument {arg.name} is type {cats[0].name}"
                    " out of proper order"
                )
            current_argtype = i
            self.lint_argument(op, arg)
        for typesupport in op.typesupports:
            self.lint_typesupport(typesupport, op)

    def lint(self, args):
        # Generate version information
        major = self.spec.version_major
        minor = self.spec.version_minor
        patch = self.spec.version_patch
        if args.verbose:
            print(f"Running on specification version {major}.{minor}.{patch}")
        for group in self.spec.operatorgroups:
            for op in group.operators:
                self.lint_operator(op)
        for enum in self.spec.enums:
            self.lint_enum(enum)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--xml", required=True, help="Path to specification XML")
    parser.add_argument(
        "-v",
        "--verbose",
        required=False,
        action="store_true",
        help="Run in verbose mode",
    )
    args = parser.parse_args()

    try:
        spec = tosa.TOSASpec(args.xml)
    except RuntimeError as e:
        print(f"Failure reading/validating XML spec: {str(e)}")
        exit(1)

    generator = TOSASpecLinter(spec)
    generator.lint(args)
    if generator.warnings > 0:
        print(f"{generator.warnings} warnings encountered")
        exit(1)
    exit(0)
