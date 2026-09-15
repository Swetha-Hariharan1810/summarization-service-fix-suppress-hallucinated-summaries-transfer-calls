FROM ubuntu:22.04 as base
WORKDIR /home/ubuntu/codebase/
# install conda toolkit

ENV PATH="/root/miniconda3/bin:${PATH}"
ARG PATH="/root/miniconda3/bin:${PATH}"
ARG DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# ARG DEV_AWS_KEY
# ARG DEV_AWS_SECRET
# ARG DEV_AWS_REGION

# ARG BIRCHSUMM_AWS_LOGIN
# ARG BIRCHSUMM_EXPIRE
# ARG BIRCHSUMM_AUTH_SERVER
# ARG BIRCHSUMM_DELAY

RUN apt update -y && apt upgrade -y && apt install git wget curl build-essential zip iputils-ping libcurl4-openssl-dev openssl libssl-dev -y && rm -rf /var/lib/apt/lists/*

# Miniconda3-py39_4.12.0-Linux-x86_64.sh
RUN wget \
    https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh \
    && mkdir /root/.conda \
    && bash Miniconda3-latest-Linux-x86_64.sh -b \
    && rm -f Miniconda3-latest-Linux-x86_64.sh

RUN conda install -c anaconda cmake

RUN conda install python=3.9.15
RUN conda install pytorch=1.13.0 torchaudio=0.13.0 cpuonly  -c pytorch


COPY birchsumm /home/ubuntu/codebase/
COPY data/jit-model /home/ubuntu/codebase/data/model

RUN python setup.py build_ext -j 4 bdist_wheel && pip install .
RUN rm -fr summ_service_jit

RUN wget "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -O "awscliv2.zip"
RUN unzip awscliv2.zip
RUN ./aws/install

CMD python -m summ_service_jit.main --model-dir data/model --input-dir data/input-transcripts --output-dir data/output-summaries --log-dir /tmp/summ-logs/
