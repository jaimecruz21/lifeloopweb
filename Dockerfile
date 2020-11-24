FROM python:3.6.4-alpine3.7
RUN apk update && apk upgrade && apk --update add \
    libstdc++ tzdata ca-certificates build-base libffi-dev zlib-dev bash mysql-client openssl git yarn

WORKDIR /code
COPY . /code
COPY docker/web_entrypoint.sh /code

RUN export DOCKERIZE_VERSION=v0.6.0 \
    && wget https://github.com/jwilder/dockerize/releases/download/$DOCKERIZE_VERSION/dockerize-alpine-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
        && tar -C /usr/local/bin -xzvf dockerize-alpine-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
            && rm dockerize-alpine-linux-amd64-$DOCKERIZE_VERSION.tar.gz

RUN pip install -r requirements.txt && pip install -e .
