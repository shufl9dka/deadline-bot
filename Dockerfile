FROM python:3.9

RUN mkdir /app
WORKDIR /app

ENV DB_HOST=db
ENV DB_USER=postgres
ENV DB_NAME=deadline_bot_db
ENV DB_PASSWORD=71bR!WTSe9s7

ENV REDIS_HOST=redis
ENV REDIS_PASSWORD=9BJ@rfds62n8

ENV BOT_TOKEN=5988718115:AAHaViWvFFzjQM1p5dI0044bFT61O4O-JLo

ADD . /app/
ADD requirements.txt requirements.txt

RUN apt update -y
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

ENTRYPOINT ["python", "main.py"]