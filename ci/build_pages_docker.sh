#!/usr/bin/env bash
#
# SPDX-FileCopyrightText: 2026 Arm Limited and/or its affiliates <open-source-office@arm.com>
# SPDX-License-Identifier: Apache-2.0

set -Eeuo pipefail

# Tags of the specification releases to build
RELEASE_TAGS=(v1.0.0 v1.0.1 v1.0.2)

build() {
  make -C "$1" html
  mkdir -p "$2"
  cp -r "$1/out/html/." "$2/"
  mv "$2/tosa_spec.html" "$2/index.html"
}

rm -rf out/pages

# Build 'main' branch
build . out/pages

# Build tagged releases
for tag in "${RELEASE_TAGS[@]}"; do
  source_dir=$(mktemp -d)
  git worktree add --detach "$source_dir" "refs/tags/$tag"
  trap 'git worktree remove --force "$source_dir"' EXIT
  build "$source_dir" "out/pages/releases/$tag"
  git worktree remove --force "$source_dir"
  trap - EXIT
done
