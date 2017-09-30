FROM python:2.7
MAINTAINER 777arc <marcll@vt.edu>

ENV PYTHONUNBUFFERED 1  

COPY requirements.txt /config/requirements.txt
COPY cgran/ /src/cgran
COPY ootlist /src/ootlist
COPY manage.py /src/
COPY db-manually-annotated.yaml /src/
COPY docker-entrypoint.sh /src/

RUN pip install -r /config/requirements.txt

WORKDIR /src

CMD [ "/src/docker-entrypoint.sh" ]
