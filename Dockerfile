FROM python:3.4
RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

VOLUME /mapping

COPY . /usr/src/app/
RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "-u","/usr/src/app/server.py"] 
