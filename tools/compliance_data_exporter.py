# Copyright (c) 2024, ARM Limited.
# SPDX-License-Identifier: Apache-2.0
import os

from tosa import TOSAOperator
from tosa import TOSAOperatorArgument


validation_term_mapping_profile = {
    "PRO-INT": "Profile::pro_int",
    "PRO-FP": "Profile::pro_fp",
    "EXT-INT16": "Extension::int16",
    "EXT-INT4": "Extension::int4",
    "EXT-BF16": "Extension::bf16",
    "EXT-FP8E4M3": "Extension::fp8e4m3",
    "EXT-FP8E5M2": "Extension::fp8e5m2",
    "EXT-FFT": "Extension::fft",
    "EXT-SHAPE": "Extension::shape",
    "EXT-VARIABLE": "Extension::variable",
}

validation_term_mapping_type = {
    "bool_t": "boolT",
    "i4_t": "i4T",
    "i8_t": "i8T",
    "i16_t": "i16T",
    "i32_t": "i32T",
    "i48_t": "i48T",
    "bf16_t": "bf16T",
    "fp16_t": "fp16T",
    "fp32_t": "fp32T",
    "fp8e4m3_t": "fp8e4m3T",
    "fp8e5m2_t": "fp8e5m2T",
}


def convert_to_export_format_op(op_name: str):
    return "tosa." + op_name.lower()


def convert_to_export_format_profile(profile: str):
    converted_profile = validation_term_mapping_profile.get(profile)
    if not converted_profile:
        raise RuntimeError(f"Invalid profile name {profile}")
    return converted_profile


def convert_to_export_format_type(ty: str):
    converted_ty = validation_term_mapping_type.get(ty)
    if not converted_ty:
        raise RuntimeError(f"Invalid element type name {ty}")
    return converted_ty


def is_matched_print_mode(profile: str, print_mode: str) -> bool:
    if print_mode == "Extension":
        return True if "EXT" in profile else False
    if print_mode == "Profile":
        return True if "EXT" not in profile else False
    raise RuntimeError(f"Invalid printing mode {print_mode}")


# Retrieve the compliance information for the profile-based validation.
def get_profile_compliance_info(operator: TOSAOperator, print_mode: str) -> set:
    prof_info = {}

    for tysup in operator.typesupports:
        prof_set = set()
        tsmap = tysup.tymap

        for profs in tysup.profiles:
            profs = profs.split(" and ")
            for prof in profs:
                if is_matched_print_mode(prof, print_mode):
                    prof_set.add(prof)

        if len(prof_set) == 0:
            continue

        prof_list = list(prof_set)
        prof_list.sort()
        prof_str = " ".join(prof_list)

        if prof_str in prof_info.keys():
            value = prof_info[prof_str]
            value.append(tsmap)
        else:
            prof_info[prof_str] = [tsmap]

    return prof_info


# Retrieve the profile/extension dependant argurments.
def get_required_arguments_info(operator) -> list:
    # Symbolic types are formal parameters such as in_t, out_t, in_out_t, acc_t, etc.
    symbolic_types = operator.types
    args = []

    for arg in operator.arguments:
        num = len(arg.categories)
        assert num == 1, f"Argument should only have 1 category, but found {num}"

        # First, gather the input and output arguments that have symbolic
        # (non-concrete) types.

        cat = arg.categories[0].name
        if cat == "input" or cat == "output":
            # Concrete types such as mul_t and i8_t, are not necessary for the
            # type indexing.
            if arg.tensor_element_type in symbolic_types:
                args.append(arg)

        # Then, handle uncommon cases where the argument type depends on the
        # profile or extension.

        # `initial_value` of VARIABLE is Attribute type.
        if operator.name == "VARIABLE" and cat == "attribute":
            if arg.tensor_element_type in symbolic_types:
                args.append(arg)

        # `acc_type` of CONV-like ops is Attribute type.
        if arg.name == "acc_type":
            args.append(arg)

    return args


def print_condition(print_mode: str) -> str:
    output_string = ", "
    if print_mode == "Extension":
        output_string += "allOf"
    if print_mode == "Profile":
        output_string += "anyOf"
    return output_string


def print_profile(profiles: list) -> str:
    # Start of the profile/extension set, e.g. {{Profile...
    output_string = "    {{"

    for prof in profiles:
        output_string += convert_to_export_format_profile(prof)

        if not prof == profiles[-1]:
            output_string += ", "

    # End of the profile/extension set, e.g. ...pro_fp}, {
    output_string += "}, "

    return output_string


"""
  Dictionary of argument_compliances looks like:
    1: {'in_t': 'fp16_t', 'out_t': 'i32_t'}
    2: {'in_t': 'fp32_t', 'out_t': 'i32_t'}
"""


def print_argument_compliances(args: TOSAOperatorArgument, compliances: list) -> str:
    output_string = "{"
    for compl in compliances:
        # Start of the argument set
        output_string += "{"

        for arg in args:
            sym_ty = arg.tensor_element_type

            # Transform enumerated type to symbolic type.
            if sym_ty == "-":
                if not arg.type == "acc_type_t":
                    raise RuntimeError(
                        f"Type {arg.type} is not considered in the validation"
                    )
                sym_ty = "acc_t"

            if sym_ty in compl.keys():
                concrete_ty = compl[sym_ty]
                output_string += convert_to_export_format_type(concrete_ty)

                if not arg == args[-1]:
                    output_string += ", "

        # End of the argument set
        output_string += "}"
        if not compl == compliances[-1]:
            output_string += ", "

    output_string += "}"

    return output_string


"""
Desired output format looks like:
    {"tosa.depthwise_conv2d",
      {
        {{Profile::pro_int}, {{i8T, i8T, i32T, i32T}}},
        {{Profile::pro_fp},
         {{fp16T, fp16T, fp16T, fp16T},
          {fp16T, fp16T, fp16T, fp32T},
          {fp32T, fp32T, fp32T, fp32T}}}
      }
    },
"""


def print_operator(
    name: str, args: TOSAOperatorArgument, depot: dict, print_mode: str, file
) -> str:
    output_string = '{"'
    output_string += convert_to_export_format_op(name)
    # Start of the whole set of the tuple of (profile, compliances set).
    output_string += '",\n  {\n'

    cnt = 0
    # `profiles` can be a single profile or extension, or a set of combination
    # of profile and extension, e.g. {PRO-INT, PRO-FP}, {EXT-BF16 and EXT-FP8E4M3},
    # and {PRO-INT and EXT-VARIABLE}.
    for profiles, argument_compliances in depot.items():
        delimiter = " "
        # Filter out the delimiter word.
        post_profiles = profiles.split(delimiter)

        output_string += print_profile(post_profiles)

        output_string += print_argument_compliances(args, argument_compliances)

        if len(post_profiles) > 1:
            output_string += print_condition(print_mode)

        # End of each tuple of (profile, compliances set, condition).
        output_string += "}"

        cnt += 1
        if cnt < len(depot):
            output_string += ","

        output_string += "\n"

    # End of the whole set of the tuple of (profile, compliances set).
    output_string += "  }\n},\n"

    if cnt != 0:
        file.write(output_string)


# Generate output for the validation pass in MLIR
def export_operator(operator: TOSAOperator, file, print_mode: str) -> None:
    args = get_required_arguments_info(operator)

    # No compliance requirement found.
    if len(args) == 0:
        return

    """
    The layout of the `profile_compliance_depot` dictionary:
      {'profile_a, ...' : [ {sym_ty_a: param_ty_a, sym_ty_b: param_ty_b, ...},
                            {sym_ty_a: param_ty_c, sym_ty_b: param_ty_d, ...} ],
       'profile_b, ...' : [ {sym_ty_a: param_ty_a, sym_ty_b: param_ty_a, ...},
                            {sym_ty_a: param_ty_e, sym_ty_b: param_ty_f, ...} ],
       ...
      }
    """
    profile_compliance_depot = get_profile_compliance_info(operator, print_mode)

    # No profile compliance information found.
    if len(profile_compliance_depot) == 0:
        return

    print_operator(operator.name, args, profile_compliance_depot, print_mode, file)


def print_profiles_extensions(spec, outdir):
    with open(os.path.join(outdir, "compliance.profile.meta"), "w") as f:
        f.write("const OperationProfileComplianceMap profileComplianceMap = {\n")
        for group in spec.operatorgroups:
            for op in group.operators:
                export_operator(op, f, "Profile")
        f.write("};\n\n")

    with open(os.path.join(outdir, "compliance.extension.meta"), "w") as f:
        f.write("const OperationExtensionComplianceMap extensionComplianceMap = {\n")
        for group in spec.operatorgroups:
            for op in group.operators:
                export_operator(op, f, "Extension")
        f.write("};\n")
