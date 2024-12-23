FROM python:3.12.8-bullseye

# timezone
ENV TZ=Asia/Tokyo

RUN apt-get update

# apt-gets
RUN apt-get install -y \
    git \
    wget \
    curl \
    vim \
    git-lfs \
    sqlite3 \
    texlive-full

RUN git lfs install

RUN pip install jupyterlab
COPY requirements.txt ./
RUN pip install -r ./requirements.txt