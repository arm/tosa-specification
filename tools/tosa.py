#!/usr/bin/env python3
# Copyright (c) 2023,2026, ARM Limited.
# SPDX-License-Identifier: Apache-2.0
import itertools
import re
import xml.etree.ElementTree as ET


TYPE_SET_VALUE_EXPANSIONS = {
    "bs32_fp8ue8m0_set_t": (
        "bs32_fp8ue8m0_fp8e4m3_t",
        "bs32_fp8ue8m0_fp8e5m2_t",
        "bs32_fp8ue8m0_fp6e3m2_t",
        "bs32_fp8ue8m0_fp6e2m3_t",
        "bs32_fp8ue8m0_fp4e2m1_t",
        "bs32_fp8ue8m0_mxint8_t",
    ),
}

DEDUCED_EXTENSION_TYPE_MAPPING = {
    "i64_t": ["EXT-INT64"],
    "i16_t": ["EXT-INT16"],
    "i4_t": ["EXT-INT4"],
    "bf16_t": ["EXT-BF16"],
    "fp8e4m3_t": ["EXT-FP8E4M3"],
    "fp8e5m2_t": ["EXT-FP8E5M2"],
    "fp8ue8m0_t": ["EXT-MX-COMMON"],
    "fp4e2m1_t": ["EXT-MX-FP4E2M1"],
    "fp6e2m3_t": ["EXT-MX-FP6E2M3"],
    "fp6e3m2_t": ["EXT-MX-FP6E3M2"],
    "mxint8_t": ["EXT-MX-INT8"],
    "bs32_fp8ue8m0_fp8e4m3_t": ["EXT-MX-COMMON", "EXT-MX-FP8E4M3"],
    "bs32_fp8ue8m0_fp8e5m2_t": ["EXT-MX-COMMON", "EXT-MX-FP8E5M2"],
    "bs32_fp8ue8m0_fp6e3m2_t": ["EXT-MX-COMMON", "EXT-MX-FP6E3M2"],
    "bs32_fp8ue8m0_fp6e2m3_t": ["EXT-MX-COMMON", "EXT-MX-FP6E2M3"],
    "bs32_fp8ue8m0_fp4e2m1_t": ["EXT-MX-COMMON", "EXT-MX-FP4E2M1"],
    "bs32_fp8ue8m0_mxint8_t": ["EXT-MX-COMMON", "EXT-MX-INT8"],
}


def deduce_extensions(tsmap):
    extensions = set()
    for ty in tsmap.values():
        extensions.update(DEDUCED_EXTENSION_TYPE_MAPPING.get(ty, []))
    return extensions


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


class TOSAProfile:
    def __init__(self, profile, name, description, status):
        self.profile = profile
        self.name = name
        self.description = description
        self.status = status
        self.ops = []


class TOSAProfileExtension:
    def __init__(self, name, description, status, profiles):
        self.name = name
        self.description = description
        self.status = status
        self.profiles = profiles
        self.ops = []


class TOSAEnum:
    def __init__(self, name, description, values, extension):
        self.name = name
        self.description = description
        self.values = values
        self.extension = extension


class TOSALevel:
    def __init__(self, name, desc, maximums):
        self.name = name
        self.desc = desc
        self.maximums = maximums


class TOSAOperatorArgument:
    def __init__(
        self,
        name,
        description,
        categories,
        ty,
        elty,
        slty,
        shape,
        levellimits,
        rank,
        optional,
        ctc,
        ctc_remove,
    ):
        assert isinstance(optional, bool)
        self.name = name
        self.description = description
        self.categories = categories
        self.type = ty
        self.tensor_element_type = elty
        self.tensor_element_scale_type = slty
        self.shape = shape
        self.levellimits = levellimits
        self.rank = rank
        self.optional = optional
        self.ctc = ctc
        self.ctc_remove = ctc_remove


class TOSAOperatorDataTypeSupport:
    def __init__(
        self,
        mode,
        generated_tuples,
        version_added,
        profiles,
        tskeys,
        type_sets=None,
        type_bindings=None,
        type_binding_same_as=None,
    ):
        if len(generated_tuples) == 0:
            raise RuntimeError(f"Typesupport {mode} has no generated tuples")
        self.mode = mode
        self.generated_tuples = [dict(tytuple) for tytuple in generated_tuples]
        tuple_keys = set(self.generated_tuples[0].keys())
        for tytuple in self.generated_tuples[1:]:
            if set(tytuple.keys()) != tuple_keys:
                raise RuntimeError(
                    f"Typesupport {mode} has inconsistent generated tuple keys"
                )
        self.tymap = self.generated_tuples[0]  # For fixed type_support with no Sets
        self.profiles = profiles
        self.version_added = version_added
        self.tskeys = tskeys
        self.type_sets = list(type_sets or [])
        self.type_bindings = dict(type_bindings or {})
        self.type_binding_same_as = dict(type_binding_same_as or {})


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
        self.profiles = []
        self.profile_extensions = []
        self.levels = []
        self.operatorgroups = []
        self.enums = []
        self.__load_spec()

    def __load_spec(self):
        self.__load_version()
        for profile in self.xmlroot.findall("./profiles/profile"):
            self.profiles.append(self.__load_profile(profile))
        for profile_ext in self.xmlroot.findall(
            "./profile_extensions/profile_extension"
        ):
            self.profile_extensions.append(self.__load_profile_extension(profile_ext))
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

    def __load_profile(self, xml_profile):
        profile = xml_profile.get("profile")
        name = xml_profile.get("name")
        description = xml_profile.get("description")
        status = xml_profile.get("status")
        return TOSAProfile(profile, name, description, status)

    def __load_profile_extension(self, ext):
        name = ext.get("name")
        description = ext.get("description")
        status = ext.get("status")
        profiles = [x.text for x in ext]
        return TOSAProfileExtension(name, description, status, profiles)

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
            "MAX_TENSOR_LIST_SIZE": level.get("max_tensor_list_size"),
            "MAX_SHAPE_LEN": level.get("max_shape_len"),
        }
        return TOSALevel(name, desc, maximums)

    def __load_operator_group(self, group):
        name = group.get("name")
        operators = []
        for op in group.findall("operator"):
            operators.append(self.__load_operator(op))
        return TOSAOperatorGroup(name, operators)

    def __extension_string(self, op_profile):
        tsp_name = op_profile.get("name")
        and_name = op_profile.get("and_name")
        and_name2 = op_profile.get("and_name2")
        if and_name2 is not None:
            tsp_name = " and ".join(sorted([tsp_name, and_name, and_name2]))
        elif and_name is not None:
            if and_name < tsp_name:
                tsp_name = f"{and_name} and {tsp_name}"
            else:
                tsp_name = f"{tsp_name} and {and_name}"

        return tsp_name

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
            tskeys = tysup.keys()
            tsmode = tysup.get("mode")
            tsmap = {}
            version_added = tysup.get("version_added")
            profiles = tysup.findall("op_profile")
            tsprofiles = []
            for p in profiles:
                tsp_name = self.__extension_string(p)
                tsprofiles.append(tsp_name)
            for ty in types:
                tsmap[ty] = tysup.get(ty)
            type_sets = self.__load_typesupport_sets(tysup, name, tsmode)
            expanded_type_sets = self.__expand_typesupport_sets(type_sets)
            type_bindings, type_binding_same_as = self.__load_typesupport_bindings(
                tysup, name, tsmode, types, type_sets
            )
            generated_tuples = self.__expand_typesupport_tuples(
                name,
                tsmode,
                types,
                tsmap,
                expanded_type_sets,
                type_bindings,
                type_binding_same_as,
            )
            typesupports.append(
                TOSAOperatorDataTypeSupport(
                    tsmode,
                    generated_tuples,
                    version_added,
                    tsprofiles,
                    tskeys,
                    type_sets,
                    type_bindings,
                    type_binding_same_as,
                )
            )
        return TOSAOperator(name, args, types, typesupports)

    def __load_typesupport_sets(self, tysup, op_name, mode):
        type_sets = []
        seen_names = set()
        for type_set in tysup.findall("type_set"):
            set_name = type_set.get("name")
            if set_name in seen_names:
                raise RuntimeError(
                    f"Operator {op_name} mode {mode} repeats type set {set_name}"
                )
            values = type_set.get("values").split()
            if len(values) == 0:
                raise RuntimeError(
                    f"Operator {op_name} mode {mode} has empty type set {set_name}"
                )
            type_sets.append((set_name, values))
            seen_names.add(set_name)
        return type_sets

    def __expand_typesupport_sets(self, type_sets):
        return [
            (set_name, self.__expand_type_set_values(values))
            for set_name, values in type_sets
        ]

    def __expand_type_set_values(self, values):
        expanded = []
        for value in values:
            expanded.extend(TYPE_SET_VALUE_EXPANSIONS.get(value, (value,)))

        deduplicated = []
        for value in expanded:
            if value not in deduplicated:
                deduplicated.append(value)
        return deduplicated

    def __load_typesupport_bindings(self, tysup, op_name, mode, types, type_sets):
        # See EXPECT_TYPESUPPORT comment in tosa.xsd
        type_bindings = {}
        type_binding_same_as = {}
        known_sets = {set_name for set_name, _ in type_sets}
        for type_bind in tysup.findall("type_bind"):
            ty_name = type_bind.get("type")
            set_name = type_bind.get("set")
            same_as = type_bind.get("same_as")
            if ty_name not in types:
                raise RuntimeError(
                    f"Operator {op_name} mode {mode} binds unknown type {ty_name}"
                )
            if ty_name in type_bindings:
                raise RuntimeError(
                    f"Operator {op_name} mode {mode} repeats binding for {ty_name}"
                )
            if set_name not in known_sets:
                raise RuntimeError(
                    f"Operator {op_name} mode {mode} "
                    f"references unknown type set {set_name}"
                )
            type_bindings[ty_name] = set_name
            if same_as is not None:
                type_binding_same_as[ty_name] = same_as

        for ty_name, same_as in type_binding_same_as.items():
            if same_as not in types:
                raise RuntimeError(
                    f"Operator {op_name} mode {mode} ties {ty_name} "
                    f"to unknown type {same_as}"
                )
            if same_as not in type_bindings:
                raise RuntimeError(
                    f"Operator {op_name} mode {mode} ties {ty_name} "
                    f"to unbound type {same_as}"
                )
            if type_bindings[ty_name] != type_bindings[same_as]:
                raise RuntimeError(
                    f"Operator {op_name} mode {mode} ties {ty_name} "
                    f"to {same_as} with a different type set"
                )

        for ty_name in type_binding_same_as:
            seen = set()
            current = ty_name
            while current in type_binding_same_as:
                if current in seen:
                    raise RuntimeError(
                        f"Operator {op_name} mode {mode} has a same_as cycle "
                        f"starting at {ty_name}"
                    )
                seen.add(current)
                current = type_binding_same_as[current]

        return type_bindings, type_binding_same_as

    def __expand_typesupport_tuples(
        self,
        op_name,
        mode,
        types,
        tsmap,
        type_sets,
        type_bindings,
        type_binding_same_as,
    ):
        for ty_name in type_bindings:
            if tsmap.get(ty_name) is not None:
                raise RuntimeError(
                    f"Operator {op_name} mode {mode} "
                    f"binds {ty_name} and sets it explicitly"
                )

        if len(type_bindings) == 0:
            return [tsmap]

        type_sets_map = {set_name: values for set_name, values in type_sets}
        bound_types = [
            ty_name
            for ty_name in types
            if ty_name in type_bindings and ty_name not in type_binding_same_as
        ]
        bound_value_lists = [
            type_sets_map[type_bindings[ty_name]] for ty_name in bound_types
        ]

        generated_tuples = []
        for bound_values in itertools.product(*bound_value_lists):
            expanded = dict(tsmap)
            for ty_name, value in zip(bound_types, bound_values):
                expanded[ty_name] = value
            for ty_name in types:
                if ty_name not in type_binding_same_as:
                    continue
                same_as = ty_name
                while same_as in type_binding_same_as:
                    same_as = type_binding_same_as[same_as]
                expanded[ty_name] = expanded[same_as]
            generated_tuples.append(expanded)

        return generated_tuples

    def __load_operator_argument(self, arg, op_name):
        name = arg.get("name")
        desc = arg.find("description").text.strip()
        argcats = []
        argtype = arg.get("type")
        argtelty = arg.get("tensor-element-type")
        argtslty = arg.get("tensor-element-scale-type", "-")
        shape = arg.get("shape")
        levellimits = []
        rank = []
        optional = arg.get("optional", "false") == "true"

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

        ctc = []
        ctc_elements = arg.find("ctc")
        if ctc_elements is not None:
            for profile in ctc_elements.findall("op_profile"):
                ctc.append(profile.get("name"))

        ctc_remove = []
        ctc_remove_elements = arg.find("ctc_remove")
        if ctc_remove_elements is not None:
            for profile in ctc_remove_elements.findall("op_profile"):
                ctc_remove.append(profile.get("name"))

        op_profile = arg.find("op_profile")
        if op_profile is not None:
            print("found")
            s = self.__extension_string(op_profile)
            desc = f"{desc}. Requires the following extensions: {s}"

        return TOSAOperatorArgument(
            name,
            desc,
            argcats,
            argtype,
            argtelty,
            argtslty,
            shape,
            levellimits,
            rank,
            optional,
            ctc,
            ctc_remove,
        )

    def __load_enum(self, arg):
        name = arg.get("name")
        desc = arg.get("description").strip()
        enumextension = arg.get("extension", "")
        values = []
        for val in arg.findall("enumval"):
            valextension = [val.get("extension", ""), val.get("or_extension", "")]
            values.append(
                (
                    val.get("name"),
                    val.get("value"),
                    val.get("description"),
                    valextension,
                )
            )
        return TOSAEnum(name, desc, values, enumextension)

    def get_enum_by_name(self, name):
        for e in self.enums:
            if e.name == name:
                return e
