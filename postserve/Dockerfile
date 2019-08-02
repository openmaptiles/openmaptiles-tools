FROM python:3.6
LABEL MAINTAINER "Yuri Astrakhan <YuriAstrakhan@gmail.com>"

WORKDIR /usr/src/app

# Copy requirements.txt first to avoid pip install on every code change
COPY ./requirements.txt /usr/src/app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /usr/src/app/

ENTRYPOINT ["python", "server.py"]
