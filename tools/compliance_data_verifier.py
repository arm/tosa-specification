#!/usr/bin/env python3
# Copyright (c) 2024-2025, ARM Limited.
# SPDX-License-Identifier: Apache-2.0
import re

import regex

op_list = [
    "argmax",
    "avg_pool2d",
    "conv2d",
    "conv3d",
    "depthwise_conv2d",
    "fft2d",
    "fully_connected",
    "matmul",
    "max_pool2d",
    "rfft2d",
    "transpose_conv2d",
    "clamp",
    "erf",
    "sigmoid",
    "tanh",
    "add",
    "arithmetic_right_shift",
    "bitwise_and",
    "bitwise_or",
    "bitwise_xor",
    "intdiv",
    "logical_and",
    "logical_left_shift",
    "logical_right_shift",
    "logical_or",
    "logical_xor",
    "maximum",
    "minimum",
    "mul",
    "pow",
    "sub",
    "table",
    "abs",
    "bitwise_not",
    "ceil",
    "clz",
    "cos",
    "exp",
    "floor",
    "log",
    "logical_not",
    "negate",
    "reciprocal",
    "rsqrt",
    "select",
    "sin",
    "equal",
    "greater",
    "greater_equal",
    "reduce_all",
    "reduce_any",
    "reduce_max",
    "reduce_min",
    "reduce_product",
    "reduce_sum",
    "concat",
    "pad",
    "reshape",
    "reverse",
    "slice",
    "tile",
    "transpose",
    "gather",
    "scatter",
    "resize",
    "cast",
    "rescale",
    "const",
    "identity",
    "custom",
    "cond_if",
    "while_loop",
    "variable",
    "variable_write",
    "variable_read",
    "add_shape",
    "concat_shape",
    "const_shape",
    "dim",
    "div_shape",
    "mul_shape",
    "sub_shape",
    "cast_to_block_scaled",
    "cast_from_block_scaled",
    "matmul_t_block_scaled",
    "conv2d_block_scaled",
]

profile_list = [
    "Profile::pro_int",
    "Profile::pro_fp",
    "Extension::int64",
    "Extension::int16",
    "Extension::int4",
    "Extension::bf16",
    "Extension::fp8e4m3",
    "Extension::fp8e5m2",
    "Extension::fft",
    "Extension::variable",
    "Extension::shape",
    "Extension::mxfp",
    "Extension::mxfp_conv",
]

type_list = [
    "boolT",
    "i4T",
    "i8T",
    "i16T",
    "i32T",
    "i48T",
    "i64T",
    "bf16T",
    "fp16T",
    "fp32T",
    "fp8e4m3T",
    "fp8e5m2T",
    "fp8ue8m0T",
    "fp6e3m2T",
    "fp6e2m3T",
    "fp4e2m1T",
    "mxint8T",
]

cond_list = [
    "anyOf",
    "allOf",
    "invalid",
]


def capture_data_between_curly_brackets(x: str):
    if x.count("{") != x.count("}"):
        raise RuntimeError("syntax error: curly bracket pair mismatch")

    return regex.findall(r"{((?>[^{}]+|(?R))*)}", x)


def verify_condition_if_present(x: str) -> None:
    last_bracket = x.rfind("}") + 1
    if last_bracket != len(x):
        i = last_bracket + 1
        cond = x[i:]
        if cond not in cond_list:
            raise RuntimeError(f"invalid condition name {cond}")


"""
The format of operation look like:
    "tosa.add", {
        {{Profile::pro_int,Profile::pro_fp}, {
            {{i32T,i32T,i32T}, SpecificationVersion::V_1_0}}},
        {{Profile::pro_fp}, {
            {{fp16T,fp16T,fp16T}, SpecificationVersion::V_1_0},
            {{fp32T,fp32T,fp32T}, SpecificationVersion::V_1_0}}}}
"""


def verify_operation_compliance_syntax(op) -> None:
    op_name = re.findall(r"\"tosa.*\"", str(op))
    assert len(op_name) == 1

    if str(op_name)[8:-3] not in op_list:
        raise RuntimeError(f"invalid tosa operation name {op_name}")

    """
    Capture all compliance tuples associated with the current operation.
        e.g. ['{{Profile::pro_int,Profile::pro_fp},
                {{{i32T,i32T,i32T}, SpecificationVersion::V_1_0}}},
               {{Profile::pro_fp},
                {{{fp16T,fp16T,fp16T}, SpecificationVersion::V_1_0},
                {{fp32T,fp32T,fp32T}, SpecificationVersion::V_1_0}}}']
    """
    comps = capture_data_between_curly_brackets(str(op))

    """
    Capture again to make every compliance separate from each other.
        e.g. ['{Profile::pro_int,Profile::pro_fp},
                {{{i32T,i32T,i32T}, SpecificationVersion::V_1_0}}',
              '{{Profile::pro_fp},
                {{{fp16T,fp16T,fp16T}, SpecificationVersion::V_1_0},
                {{fp32T,fp32T,fp32T}, SpecificationVersion::V_1_0}}}']
    """
    comps = capture_data_between_curly_brackets(str(comps))

    for comp in comps:
        verify_condition_if_present(comp)

        profiles_and_type_sets = capture_data_between_curly_brackets(str(comp))
        assert len(profiles_and_type_sets) == 2

        for prof in profiles_and_type_sets[0].split(","):
            if prof not in profile_list:
                raise RuntimeError(f"invalid profile name {prof}")

        """
        Make every type set separate from each other, without versioning.
            {{fp16T,fp16T,fp16T}, SpecificationVersion::V_1_0},
            {{fp16T,fp32T,fp16T}, SpecificationVersion::V_1_0},
            {{fp32T,fp32T,fp32T}, SpecificationVersion::V_1_0}

            becomes

            ['fp16T,fp16T,fp16T',
             'fp16T,fp32T,fp16T',
             'fp32T,fp32T,fp32T']
        """
        type_set_and_version = capture_data_between_curly_brackets(
            str(profiles_and_type_sets[1])
        )
        type_sets = capture_data_between_curly_brackets(str(type_set_and_version))

        for types in type_sets:
            for ty in types.split(","):
                if ty not in type_list:
                    raise RuntimeError(f"invalid type name {ty}")


def test_unknown_op():
    unknown_op = '"tosa.dummy",{{{Profile::pro_int},{{i8T,i32T}}}}'
    try:
        verify_operation_compliance_syntax(unknown_op)
    except Exception as e:
        assert "invalid tosa operation name" in str(e)


def test_unknown_prof():
    unknown_prof = '"tosa.add",{{{Profile::dummy},{{i8T,i32T}}}}'
    try:
        verify_operation_compliance_syntax(unknown_prof)
    except Exception as e:
        assert "invalid profile name" in str(e)


def test_unknown_extension():
    unknown_ext = '"tosa.add",{{{Extension::bf16, Extension::dummy},{{i8T,i32T}}}}'
    try:
        verify_operation_compliance_syntax(unknown_ext)
    except Exception as e:
        assert "invalid profile name" in str(e)


def test_unknown_type():
    unknown_type = '"tosa.add",{{{Profile::pro_fp},{{i128T,i32T}}}}'
    try:
        verify_operation_compliance_syntax(unknown_type)
    except Exception as e:
        assert "invalid type name" in str(e)


def test_unknown_condition():
    unknown_cond = '"tosa.dim",{{{Extension::bf16,Extension::fp8e4m3},{{bf16T}},dummy}}'
    try:
        verify_operation_compliance_syntax(unknown_cond)
    except Exception as e:
        assert "invalid condition name" in str(e)


def test_unknown_syntax():
    invalid_syntax = '"tosa.sub",{{{Profile::pro_fp},{{i8T,i32T}}}}}'
    try:
        verify_operation_compliance_syntax(invalid_syntax)
    except Exception as e:
        assert "curly bracket pair mismatch" in str(e)

    invalid_syntax2 = '"tosa.mul",{{{{Profile::pro_fp},{{i8T,i32T}}}}'
    try:
        verify_operation_compliance_syntax(invalid_syntax2)
    except Exception as e:
        assert "curly bracket pair mismatch" in str(e)


def self_sanity_check() -> None:
    test_unknown_op()
    test_unknown_prof()
    test_unknown_extension()
    test_unknown_type()
    test_unknown_condition()
    test_unknown_syntax()


if __name__ == "__main__":
    import argparse

    self_sanity_check()

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input", required=True, help="Path to the generated compliance file"
    )
    args = parser.parse_args()

    with open(args.input, "r") as file:
        file_content = file.read()

        # Concatenate multiple lines into single line.
        split_text = file_content.split("\n")
        # Remove redundant spaces.
        clean_text = "".join(str(split_text).split())

        start_pattern = "={"
        end_pattern = "};"
        start_idx = clean_text.index(start_pattern) + len(start_pattern)
        end_idx = clean_text.index(end_pattern)
        core_text = clean_text[start_idx:end_idx]
        ops = capture_data_between_curly_brackets(core_text)

        for op in ops:
            verify_operation_compliance_syntax(op)
