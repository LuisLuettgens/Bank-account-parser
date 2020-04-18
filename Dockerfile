FROM jupyter/datascience-notebook

USER root

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update

RUN apt-get install -y git-all

RUN cd work && \
    git clone https://github.com/LuisLuettgens/DKB-bank-account-parser.git

RUN cd work/DKB-bank-account-parser && \
    git pull

RUN apt-get update && \
    apt-get -y install python3-pip

RUN pip3 install -U numpy

RUN pip3 install pandas

ADD 1036976429_v4.csv work/DKB-bank-account-parser

RUN usermod -aG sudo jovyan

RUN chmod -R 777 work/DKB-bank-account-parser