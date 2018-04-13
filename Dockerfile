FROM tiangolo/uwsgi-nginx-flask:python3.6-alpine3.7
MAINTAINER Le Minh Tri

RUN apk update --no-cache

COPY ./requirements.txt /tmp/

RUN pip3 install --no-cache-dir --upgrade pip
RUN pip3 install -r /tmp/requirements.txt

COPY ./app /app

ENV FLASK_APP=app/main.py
