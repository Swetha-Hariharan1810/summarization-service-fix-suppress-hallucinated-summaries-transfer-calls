# Two stages on purpose.
#
# The compiler toolchain drags in linux-libc-dev (build-essential -> libc6-dev
# -> linux-libc-dev), which is nothing but kernel headers but still carries
# every open kernel CVE into the scan report. Confining it to a builder stage
# that is never shipped keeps those findings out of the published image.
#
# The runtime stage installs with --no-install-recommends so python3-pip cannot
# pull python3-dev (and libc6-dev, and the headers) back in behind our back.

# --------------------------------------------------------------------------
# builder - has the toolchain; nothing from this stage ships except ~/.local
# --------------------------------------------------------------------------
FROM ubuntu:22.04 AS builder

ARG USER_ID=999
ARG GROUP_ID=1099
ARG USER_NAME=appuser
ARG GROUP_NAME=appgroup
ARG DEBIAN_FRONTEND=noninteractive

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update -y \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-dev \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN addgroup --gid $GROUP_ID $GROUP_NAME \
    && adduser --disabled-password --gecos '' --uid $USER_ID --gid $GROUP_ID --home /home/$USER_NAME $USER_NAME \
    && chown -R $USER_NAME:$GROUP_NAME /home/$USER_NAME

WORKDIR /home/$USER_NAME
USER $USER_NAME

# Everything below installs into /home/appuser/.local, which is the only tree
# the runtime stage copies out.
COPY --chown=$USER_NAME:$GROUP_NAME ./requirements.txt ./requirements.txt
RUN pip install --upgrade pip && pip install -r ./requirements.txt

RUN pip install torch==2.0.0+cpu torchaudio==2.0.1 --extra-index-url https://download.pytorch.org/whl/cpu

COPY --chown=$USER_NAME:$GROUP_NAME ./src ./src

WORKDIR /home/$USER_NAME/src/fairseqForkSepFix
RUN python3 setup.py build_ext --inplace
RUN pip install .

# The test dependencies are installed here, not at container start, so that the
# runtime stage does not need python3-pip. docker-compose.ci.yaml used to run
# "pip install -r src/summ_service/test/requirements.txt" as its first command;
# that line is gone now and these packages arrive through the .local copy.
WORKDIR /home/$USER_NAME
RUN pip install -r ./src/summ_service/test/requirements.txt

# --------------------------------------------------------------------------
# runtime - interpreter and libraries only, no compiler, no kernel headers
# --------------------------------------------------------------------------
FROM ubuntu:22.04 AS runtime

ARG USER_ID=999
ARG GROUP_ID=1099
ARG USER_NAME=appuser
ARG GROUP_NAME=appgroup
ARG DEBIAN_FRONTEND=noninteractive

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/home/${USER_NAME}/.local/bin:${PATH}"

# No python3-pip on purpose. Ubuntu 22.04 ships pip 22.0.2, which vendors
# certifi 2022.x in pip/_vendor, and no fixed package exists for jammy - that
# bundled copy is CVE-2023-37920 (critical) and carries the msgpack and urllib3
# findings too. Everything the image needs is installed in the builder stage and
# arrives through the .local copy below, so pip is not needed at run time.
#
# ca-certificates was previously pulled in as a dependency of python3-pip and is
# listed explicitly now so TLS verification keeps working.
#
# libstdc++6/libgomp1 are the shared runtime libraries the compiled extensions
# and torch link against - runtime libs only, no headers, so they bring no
# linux-libc-dev with them.
RUN apt-get update -y \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
        python3 \
        ca-certificates \
        libstdc++6 \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN addgroup --gid $GROUP_ID $GROUP_NAME \
    && adduser --disabled-password --gecos '' --uid $USER_ID --gid $GROUP_ID --home /home/$USER_NAME $USER_NAME \
    && chown -R $USER_NAME:$GROUP_NAME /home/$USER_NAME

WORKDIR /home/$USER_NAME
USER $USER_NAME

# Site-packages and the in-place built extensions, exactly as the builder left
# them.
COPY --from=builder --chown=$USER_NAME:$GROUP_NAME /home/${USER_NAME}/.local /home/${USER_NAME}/.local
COPY --from=builder --chown=$USER_NAME:$GROUP_NAME /home/${USER_NAME}/src /home/${USER_NAME}/src
