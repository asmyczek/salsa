FROM python:3.8.5-slim

ARG CONFIG="config.json"

MAINTAINER Adam Smyczek "adamsmyczek@gmail.com"
LABEL python_version="3.8.5"

COPY ./requirements.txt /requirements.txt
COPY ./salsa /salsa
COPY ./service /service
COPY ./docker/openssl.cnf /etc/ssl/openssl.cnf
COPY ./${CONFIG} /config.json

WORKDIR /

RUN pip install -r requirements.txt

CMD [ "python", "-m", "service" ]
