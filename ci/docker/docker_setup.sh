#!/usr/bin/env bash
#
# SPDX-FileCopyrightText: 2026 Arm Limited and/or its affiliates <open-source-office@arm.com>
# SPDX-License-Identifier: Apache-2.0

# Provisioning helper for Docker builds.
# Encapsulates 'how to do' steps so the Dockerfile can stay declarative.

set -Eeuo pipefail

# Defaults (can be overridden by Docker ARG/ENV)
: "${VENV_PATH:=/opt/venv}"
: "${DEBIAN_FRONTEND:=noninteractive}"

log() { printf "\n\033[1;34m[provision]\033[0m %s\n" "$*"; }

apt_clean() {
  rm -rf /var/lib/apt/lists/* || true
}

install_core_deps() {
  log "Installing core build dependencies"
  apt-get update
  apt-get install -y --no-install-recommends \
    asciidoc \
    asciidoctor \
    aspell-en \
    git \
    make \
    ruby-asciidoctor-pdf \
    sudo

  apt-get clean
  apt_clean
}

install_python() {
  log "Installing Python 3.12 and creating virtualenv at ${VENV_PATH}"
  apt-get update
  apt-get install -y --no-install-recommends \
    python3.12 \
    python3.12-venv \
    python3.12-dev
  apt-get clean
  apt_clean

  update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 100
  update-alternatives --set python3 /usr/bin/python3.12

  python3.12 -m venv "${VENV_PATH}"
  "${VENV_PATH}/bin/python" -m pip install --upgrade \
    pip \
    pre-commit \
    regex \
    setuptools \
    wheel

  log "Python versions"
  python3 --version
  "${VENV_PATH}/bin/python" --version
}

setup_user() {
  : "${USERNAME:?USERNAME is required}"
  : "${USER_UID:?USER_UID is required}"
  : "${USER_GID:?USER_GID is required}"

  log "Setting up user ${USERNAME} (uid=${USER_UID}, gid=${USER_GID})"
  # Resolve (or create) group
  if getent group "${USER_GID}" >/dev/null; then
    GROUP_NAME="$(getent group "${USER_GID}" | cut -d: -f1)"
  elif getent group "${USERNAME}" >/dev/null; then
    GROUP_NAME="${USERNAME}"
    groupmod -g "${USER_GID}" "${GROUP_NAME}" || true
  else
    GROUP_NAME="${USERNAME}"
    groupadd -g "${USER_GID}" "${GROUP_NAME}"
  fi

  # Resolve (or create) user
  if id -u "${USERNAME}" >/dev/null 2>&1; then
    usermod -u "${USER_UID}" -g "${USER_GID}" "${USERNAME}" || true
  else
    useradd -m -u "${USER_UID}" -g "${USER_GID}" "${USERNAME}"
  fi

  # Sudo (dev convenience; remove for locked-down CI)
  usermod -aG sudo "${USERNAME}" || true
  echo "${USERNAME} ALL=(ALL) NOPASSWD:ALL" | tee "/etc/sudoers.d/${USERNAME}" >/dev/null
  chmod 0440 "/etc/sudoers.d/${USERNAME}"

  # Writable dirs
  mkdir -p /workspace "${VENV_PATH}"
  chown -R "${USER_UID}:${USER_GID}" "/home/${USERNAME}" "/workspace" "${VENV_PATH}"
}

usage() {
  cat >&2 <<'EOF'
Usage: docker_setup.sh <command>

Commands:
  core      Install core build dependencies
  python    Install Python 3.12 and create virtualenv
  user      Create/align user and group (requires USERNAME, USER_UID, USER_GID)

You can chain this in the Dockerfile as multiple RUN steps.
EOF
  exit 2
}

main() {
  [[ $# -ge 1 ]] || usage
  case "$1" in
    core)   install_core_deps ;;
    python) install_python ;;
    user)   setup_user ;;
    *)      usage ;;
  esac
}
main "$@"
