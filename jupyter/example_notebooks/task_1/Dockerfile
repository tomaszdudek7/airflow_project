FROM python:3.6-alpine

COPY requirements.txt /

#this will be overwriten should `docker run` pass a proper env
ENV EXECUTION_ID 111111

RUN apk add build-base
RUN apk --no-cache --update-cache add gfortran python-dev py-pip build-base wget freetype-dev libpng-dev openblas-dev

RUN pip install -r /requirements.txt

RUN mkdir notebook
RUN mkdir notebook/output

COPY code.ipynb ./notebook/code.ipynb
COPY params.yaml ./notebook/params.yaml
COPY run.sh ./notebook/run.sh

WORKDIR notebook
ENTRYPOINT ["bash", "./run.sh"]



