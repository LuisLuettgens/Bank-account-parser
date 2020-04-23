FROM jupyter/datascience-notebook:29f53f8b9927

USER root

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update && apt-get install -y git-all \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN usermod -aG sudo jovyan

RUN cd work && \
    git clone https://github.com/LuisLuettgens/Bank-account-parser.git

RUN chmod -R 777 work/DKB-bank-account-parser
