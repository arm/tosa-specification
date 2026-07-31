<!--
    SPDX-FileCopyrightText: Copyright 2026 Arm Limited and/or its affiliates <open-source-office@arm.com>
    SPDX-License-Identifier: Apache-2.0
-->

# TOSA Specification CI

## Development with Docker
This directory contains scripts and instructions for building and developing TOSA Specification using Docker. It provides helper scripts for creating development and CI images, as well as guidance for running a development shell.

### Build the image

Use the helper script (recommended):
```
# Local dev image (creates a user matching your UID/GID)
docker/build_docker.sh

# CI image (root-only)
docker/build_docker.sh --target ci -t tosa-spec:ci

# Cross-build (requires buildx)
docker/build_docker.sh --platform linux/arm64 -t tosa-spec:local-arm64
```

### Run a dev shell
Mount your project and work from /workspace:
```
docker run --rm -it -v "$PWD":/workspace -w /workspace tosa-spec:local

### Build TOSA Spec using the Docker
```
docker run --rm -it -v "$PWD":/workspace -w /workspace tosa-spec:local ci/build_spec_docker.sh