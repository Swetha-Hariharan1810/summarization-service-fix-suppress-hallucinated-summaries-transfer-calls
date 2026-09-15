FROM ubuntu:22.04 as base
RUN apt update -y && apt upgrade -y && apt install wget curl build-essential zip -y && rm -rf /var/lib/apt/lists/*

ARG USER_ID=999
ARG GROUP_ID=1099
ARG USER_NAME=appuser
ARG GROUP_NAME=appgroup

RUN addgroup --gid $GROUP_ID $GROUP_NAME \
    && adduser --disabled-password --gecos '' --uid $USER_ID --gid $GROUP_ID --home /home/$USER_NAME $USER_NAME \
    && chown -R $USER_NAME:$GROUP_NAME /home/$USER_NAME

ENV PATH="/home/${USER_NAME}/miniconda3/bin:${PATH}"
ARG PATH="/home/${USER_NAME}/miniconda3/bin:${PATH}"

USER $USER_NAME
RUN cd /home/${USER_NAME} && \
    wget \
    https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh \
    && mkdir /home/${USER_NAME}/.conda \
    && bash Miniconda3-latest-Linux-x86_64.sh -b \
    && rm -f Miniconda3-latest-Linux-x86_64.sh

RUN conda update conda && conda install python=3.9 -y

WORKDIR /home/ubuntu/codebase/

COPY ./requirements.txt ./requirements.txt
RUN pip install --upgrade pip && pip install -r ./requirements.txt

COPY --chown=$USER_NAME:$GROUP_NAME ./src /home/ubuntu/codebase/src
COPY --chown=$USER_NAME:$GROUP_NAME ./data/models /home/ubuntu/codebase/data/models
COPY --chown=$USER_NAME:$GROUP_NAME ./data/other /home/ubuntu/codebase/data/other
