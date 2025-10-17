#!/usr/bin/env bash
#
# SPDX-FileCopyrightText: 2026 Arm Limited and/or its affiliates <open-source-office@arm.com>
# SPDX-License-Identifier: Apache-2.0

set -Eeuo pipefail

PROG="$(basename "$0")"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKERFILE="$SCRIPT_DIR/Dockerfile"
CONTEXT="$SCRIPT_DIR"                     # Required because Dockerfile uses: COPY docker_setup.sh
TARGET="${TARGET:-local}"                 # local | ci
TAG="${TAG:-tosa-spec:${TARGET}}"
PLATFORM="${PLATFORM:-}"
NO_CACHE="${NO_CACHE:-0}"
PROGRESS="${PROGRESS:-auto}"              # auto|plain|tty
declare -a EXTRA_ARGS=()                  # --build-arg K=V (repeatable)

usage() {
  cat <<EOF
Usage: $PROG [options]
  -T, --target <local|ci>     Build stage (default: ${TARGET})
  -t, --tag <name>            Image tag (default: ${TAG})
  -p, --platform <plat>       Platform (e.g. linux/amd64, linux/arm64)
  -f, --file <Dockerfile>     Dockerfile path (default: docker/Dockerfile)
      --no-cache              Disable build cache
      --progress <mode>       auto|plain|tty (default: ${PROGRESS})
      --build-arg K=V         Extra build-arg (repeatable)
  -h, --help                  Show help
Env overrides: TARGET, TAG, PLATFORM, NO_CACHE, PROGRESS
EOF
}

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    -T|--target)   TARGET="$2"; shift 2;;
    -t|--tag)      TAG="$2"; shift 2;;
    -p|--platform) PLATFORM="$2"; shift 2;;
    -f|--file)     DOCKERFILE="$2"; shift 2;;
    --no-cache)    NO_CACHE=1; shift;;
    --progress)    PROGRESS="$2"; shift 2;;
    --build-arg)   EXTRA_ARGS+=("$2"); shift 2;;
    -h|--help)     usage; exit 0;;
    *) echo "Unknown option: $1" >&2; usage; exit 2;;
  esac
done

command -v docker >/dev/null || { echo "docker not found in PATH"; exit 1; }
[[ -f "$DOCKERFILE" ]] || { echo "Dockerfile not found: $DOCKERFILE"; exit 1; }
[[ -f "$SCRIPT_DIR/docker_setup.sh" ]] || { echo "docker_setup.sh not found in $SCRIPT_DIR"; exit 1; }

# Build command
flags=()
[[ -n "$PLATFORM" ]] && flags+=(--platform "$PLATFORM")
[[ "$NO_CACHE" == "1" ]] && flags+=(--no-cache)

CMD=(docker build -f "$DOCKERFILE" --target "$TARGET" -t "$TAG" --progress "$PROGRESS" "${flags[@]}")

# Pass host user only for the 'local' target
if [[ "$TARGET" == "local" ]]; then
  USERNAME="${USERNAME:-${USER:-$(id -un)}}"
  CMD+=(--build-arg "USERNAME=$USERNAME" --build-arg "USER_UID=$(id -u)" --build-arg "USER_GID=$(id -g)")
fi

# Extra build args passthrough
for a in "${EXTRA_ARGS[@]}"; do CMD+=(--build-arg "$a"); done

# Context must be docker/ because Dockerfile uses: COPY docker_setup.sh
CMD+=("$CONTEXT")

export DOCKER_BUILDKIT=${DOCKER_BUILDKIT:-1}
echo "+ ${CMD[*]}"
exec "${CMD[@]}"
