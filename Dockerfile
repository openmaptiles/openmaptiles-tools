FROM python:3.6
VOLUME /mapping

WORKDIR /usr/src/app

# Copy requirements.txt first to avoid pip install on every code change
COPY ./requirements.txt /usr/src/app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /usr/src/app/

CMD ["python", "-u","/usr/src/app/server.py"]
