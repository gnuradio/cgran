FROM python:2.7-alpine3.6
MAINTAINER 777arc <marcll@vt.edu>

ENV PYTHONUNBUFFERED 1  

COPY requirements.txt /config/requirements.txt
COPY cgran/ /src/cgran
COPY ootlist /src/ootlist
COPY manage.py /src/
COPY db-manually-annotated.yaml /src/
COPY docker-entrypoint.sh /src/

RUN apk add --no-cache \
    dumb-init \
    git \ 
    postgresql-dev \
    gcc \
    musl-dev

RUN pip install -r /config/requirements.txt

RUN \
    adduser -S cgran &&\
    chown cgran /src

USER cgran

WORKDIR /src

ENTRYPOINT [ "dumb-init" ]

CMD [ "/src/docker-entrypoint.sh" ]
