# mostly taken from https://docs.docker.com/compose/django/
FROM python:3.10
ENV PYTHONUNBUFFERED 1  
RUN mkdir /config  
ADD requirements.txt /config/
RUN pip install --upgrade pip
RUN pip install -r /config/requirements.txt
RUN mkdir /src;  
WORKDIR /src
