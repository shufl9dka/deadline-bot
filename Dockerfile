FROM python:3.9

RUN mkdir /app
WORKDIR /app

ENV DB_HOST=db
ENV DB_USER=postgres
ENV DB_NAME=deadline_bot_db
ENV DB_PASSWORD=POSTGRES_PASSWORD

ENV BOT_TOKEN=BOT:TOKEN

ADD . /app/
ADD requirements.txt requirements.txt

RUN apt update -y
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

ENTRYPOINT ["python", "-u", "main.py"]