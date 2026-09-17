FROM ubuntu:22.04 as base
WORKDIR /home/ubuntu/codebase/
ARG DEBIAN_FRONTEND=noninteractive

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

ENV PATH="/root/miniconda3/bin:${PATH}"
ARG PATH="/root/miniconda3/bin:${PATH}"
RUN apt update -y && apt upgrade -y && apt install wget curl build-essential zip -y && rm -rf /var/lib/apt/lists/*

# Miniconda3-py39_4.12.0-Linux-x86_64.sh
RUN wget \
    https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh \
    && mkdir /root/.conda \
    && bash Miniconda3-latest-Linux-x86_64.sh -b \
    && rm -f Miniconda3-latest-Linux-x86_64.sh

# python 3.10, not 3.9: requirements.txt now needs sentence-transformers
# 6.0.1 and transformers 5.17.0, both of which declare requires-python >=3.10.
RUN conda update conda && conda install python=3.10

COPY ./requirements.txt ./requirements.txt
RUN pip install --upgrade pip && pip install -r ./requirements.txt

RUN pip3 install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu117
COPY ./src ./src
RUN cd ./src/fairseqForkSepFix && python setup.py build_ext --inplace
RUN cd ./src/fairseqForkSepFix && pip install .

RUN apt-get purge -y wget curl gcc build-essential && apt-get -y autoremove
