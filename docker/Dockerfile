FROM ubuntu:23.04

RUN apt update -y \
    && apt upgrade -y \
    && apt install python3 -y \
    && apt install python3-pip -y \
    && rm -rf /var/lib/apt/lists/* \
    && apt autoremove -y \
    && apt autoclean

ARG USER_ID=999
ARG GROUP_ID=1099
ARG USER_NAME=appuser
ARG GROUP_NAME=appgroup
ARG DEBIAN_FRONTEND=noninteractive

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN addgroup --gid $GROUP_ID $GROUP_NAME \
    && adduser --disabled-password --gecos '' --uid $USER_ID --gid $GROUP_ID --home /home/$USER_NAME $USER_NAME \
    && chown -R $USER_NAME:$GROUP_NAME /home/$USER_NAME


WORKDIR /home/appuser
RUN chown -R $USER_NAME:$GROUP_NAME /home
USER $USER_NAME


COPY ./requirements.txt ./requirements.txt
RUN pip install --upgrade pip --break-system-packages && pip install -r ./requirements.txt --break-system-packages

RUN pip install torch==2.0.0+cpu torchaudio==2.0.1 --extra-index-url https://download.pytorch.org/whl/cpu  --break-system-packages

COPY --chown=$USER_NAME:$GROUP_NAME ./src ./src

WORKDIR /home/appuser/src/fairseqForkSepFix
RUN python3 setup.py build_ext --inplace
RUN pip install . --break-system-packages

WORKDIR /home/appuser/

USER root
RUN apt-get purge gcc build-essential -y && apt-get -y autoremove
ENV PATH "/home/${USER_NAME}/.local/bin:${PATH}"
USER $USER_NAME
