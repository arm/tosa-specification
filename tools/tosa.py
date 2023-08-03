#!/usr/bin/env python3
# Copyright (c) 2023, ARM Limited.
# SPDX-License-Identifier: Apache-2.0
import re
import xml.etree.ElementTree as ET

# possible shapes: shape1, [2], [N,H,W,C]
# returns (checkable, rank)
# checkable is false if shape doesn't contain []


def get_rank_from_shape(shape):
    if "[" not in shape or "[]" in shape:
        return (False, -1)
    # Check for fixed rank requirement [N]
    m = re.match(r"\[(\d+)\]", shape)
    if m:
        return (True, 1)
    # Check for comma separated rank descriptors, return count
    m = re.match(r"\[(.*)\]", shape)
    if m:
        return (True, len(m.group(1).split(",")))
    else:
        raise RuntimeError(f"Unable to parse shape {shape}")


class TOSAOperatorArgumentCategory:
    def __init__(self, name, profiles=None):
        self.name = name
        self.profiles = profiles


class TOSAEnum:
    def __init__(self, name, description, values):
        self.name = name
        self.description = description
        self.values = values


class TOSALevel:
    def __init__(self, name, desc, maximums):
        self.name = name
        self.desc = desc
        self.maximums = maximums


class TOSAOperatorArgument:
    def __init__(
        self, name, description, categories, ty, elty, shape, levellimits, rank
    ):
        self.name = name
        self.description = description
        self.categories = categories
        self.type = ty
        self.tensor_element_type = elty
        self.shape = shape
        self.levellimits = levellimits
        self.rank = rank


class TOSAOperatorDataTypeSupport:
    def __init__(self, mode, tymap, profiles=None):
        self.mode = mode
        self.tymap = tymap
        self.profiles = profiles


class TOSAOperator:
    def __init__(self, name, arguments, types, typesupports):
        self.name = name
        self.arguments = arguments
        self.types = types
        self.typesupports = typesupports


class TOSAOperatorGroup:
    def __init__(self, name, operators):
        self.name = name
        self.operators = operators


class TOSASpec:
    def __init__(self, xmlpath):
        tree = ET.parse(xmlpath)
        self.xmlroot = tree.getroot()
        self.levels = []
        self.operatorgroups = []
        self.enums = []
        self.__load_spec()

    def __load_spec(self):
        self.__load_version()
        for level in self.xmlroot.findall("./levels/level"):
            self.levels.append(self.__load_level(level))
        for group in self.xmlroot.findall("./operators/operatorgroup"):
            self.operatorgroups.append(self.__load_operator_group(group))
        for enum in self.xmlroot.findall("./enum"):
            self.enums.append(self.__load_enum(enum))

    def __load_version(self):
        version = self.xmlroot.find("./version")
        self.version_major = int(version.get("major"))
        self.version_minor = int(version.get("minor"))
        self.version_patch = int(version.get("patch"))
        if version.get("draft") == "true":
            self.version_is_draft = True
        else:
            self.version_is_draft = False

    def __load_level(self, level):
        name = level.get("name")
        desc = level.text.strip()
        maximums = {
            "MAX_RANK": level.get("max_rank"),
            "MAX_KERNEL": level.get("max_kernel"),
            "MAX_STRIDE": level.get("max_stride"),
            "MAX_SCALE": level.get("max_scale"),
            "MAX_LOG2_SIZE": level.get("max_log2_size"),
            "MAX_NESTING": level.get("max_nesting"),
        }
        return TOSALevel(name, desc, maximums)

    def __load_operator_group(self, group):
        name = group.get("name")
        operators = []
        for op in group.findall("operator"):
            operators.append(self.__load_operator(op))
        return TOSAOperatorGroup(name, operators)

    def __load_operator(self, op):
        name = op.find("name").text
        args = []
        types = []
        typesupports = []
        for arg in op.findall("arguments/argument"):
            args.append(self.__load_operator_argument(arg, name))

        # TODO add pseudo-code to operator object?

        for ty in op.findall("types/type"):
            types.append(ty.get("name"))

        for tysup in op.findall("typesupport"):
            tsmode = tysup.get("mode")
            tsmap = {}
            profiles = tysup.findall("profile")
            tsprofiles = []
            for p in profiles:
                tsprofiles.append(p.get("name"))
            for ty in types:
                tsmap[ty] = tysup.get(ty)
            typesupports.append(TOSAOperatorDataTypeSupport(tsmode, tsmap, tsprofiles))
        return TOSAOperator(name, args, types, typesupports)

    def __load_operator_argument(self, arg, op_name):
        name = arg.get("name")
        desc = arg.find("description").text.strip()
        argcats = []
        argtype = arg.get("type")
        argtelty = arg.get("tensor-element-type")
        shape = arg.get("shape")
        levellimits = []
        rank = []
        r = arg.find("rank")
        if r is not None:
            rank = [r.get("min"), r.get("max")]
            if shape == "-" and (rank[0] != "0" or rank[1] != "0"):
                raise RuntimeError(
                    "rank is not empty or non-zero, but shape is '-'"
                    f" for {op_name}: {name}"
                )
            # validate rank against the shape argument
            (shape_check, shape_rank) = get_rank_from_shape(shape)
            if shape_check and (shape_rank < int(rank[0]) or shape_rank > int(rank[1])):
                raise RuntimeError(
                    "Description of shape rank doesn't match XML rank"
                    f" min/max: {op_name} {name} shape: {shape} shape_rank: "
                    f"{shape_rank} min/max: {rank[0]} {rank[1]}"
                )
        else:
            if shape != "-":
                raise RuntimeError(
                    f"Rank not present for {op_name}: {name} when shape is {shape}"
                )
        for levellimit in arg.findall("levellimit"):
            value = levellimit.get("value")
            limit = levellimit.get("limit")
            levellimits.append([value, limit])

        cats = re.findall(
            r"(input|output|attribute)\(?([A-Z,]+)?\)?", arg.get("category")
        )
        for cat in cats:
            argcats.append(TOSAOperatorArgumentCategory(cat[0], cat[1].split(",")))

        return TOSAOperatorArgument(
            name, desc, argcats, argtype, argtelty, shape, levellimits, rank
        )

    def __load_enum(self, arg):
        name = arg.get("name")
        desc = arg.get("description").strip()
        values = []
        for val in arg.findall("enumval"):
            values.append((val.get("name"), val.get("value"), val.get("description")))
        return TOSAEnum(name, desc, values)

    def get_enum_by_name(self, name):
        for e in self.enums:
            if e.name == name:
                return e
