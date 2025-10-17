# syntax=docker/dockerfile:1.7
#
# SPDX-FileCopyrightText: 2026 Arm Limited and/or its affiliates <open-source-office@arm.com>
# SPDX-License-Identifier: Apache-2.0

# Index digest for ubuntu:24.04
ARG UBUNTU_IMAGE_SHA=9cbed754112939e914291337b5e554b07ad7c392491dba6daf25eef1332a22e8
FROM ubuntu@sha256:${UBUNTU_IMAGE_SHA} AS base

# Build/platform info
ARG TARGETPLATFORM
ARG TARGETARCH
ARG BUILDPLATFORM
RUN printf "Building on %s for %s (arch=%s)\n" "${BUILDPLATFORM}" "${TARGETPLATFORM}" "${TARGETARCH}"

ENV DEBIAN_FRONTEND=noninteractive \
    VENV_PATH=/opt/venv \
    PATH="/opt/venv/bin:${PATH}"

# Copy the provisioning script
COPY docker_setup.sh /usr/local/bin/docker_setup.sh
RUN chmod +x /usr/local/bin/docker_setup.sh

# Install core build deps
RUN /usr/local/bin/docker_setup.sh core

# Install Python 3.12 + venv + pip packages
RUN /usr/local/bin/docker_setup.sh python

############################
# local target (non-root)
############################
FROM base AS local

# User setup
ARG USERNAME
ARG USER_UID
ARG USER_GID
ENV USERNAME=${USERNAME} USER_UID=${USER_UID} USER_GID=${USER_GID}
RUN /usr/local/bin/docker_setup.sh user

USER "${USERNAME}"
WORKDIR /home/${USERNAME}
ENV HOME=/home/${USERNAME}
RUN echo "export HOME=/home/${USERNAME}" >> /home/${USERNAME}/.profile

############################
# CI target (root)
############################
FROM base AS ci

USER root
WORKDIR /workspace
ENV HOME=/root
