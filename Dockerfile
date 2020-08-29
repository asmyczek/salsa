FROM python:3.8.5-slim

ARG CONFIG="config.json"

MAINTAINER Adam Smyczek "adamsmyczek@gmail.com"

COPY ./requirements.txt /requirements.txt
COPY ./salsa /salsa
COPY ./service /service
COPY ./${CONFIG} /config.json

WORKDIR /

RUN pip install -r requirements.txt

CMD [ "python", "-m", "service" ]
