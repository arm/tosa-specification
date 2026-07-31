#!/usr/bin/env bash
#
# SPDX-FileCopyrightText: 2026 Arm Limited and/or its affiliates <open-source-office@arm.com>
# SPDX-License-Identifier: Apache-2.0

set -Eeuo pipefail

# Adds the default created venv to $PATH
PATH=/opt/venv/bin:$PATH

# Run all pre-commit checks
pre-commit run --all

# Build all related to the spec as defined by its Makefile
make all
