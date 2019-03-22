FROM python:3.6
VOLUME /mapping

LABEL MAINTAINER "Yuri Astrakhan <YuriAstrakhan@gmail.com>"

WORKDIR /usr/src/app

# Copy requirements.txt first to avoid pip install on every code change
COPY ./requirements.txt /usr/src/app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /usr/src/app/

ENTRYPOINT ["python", "server.py"]

# Users can easily override prepared file with their own:
#
#   docker run -it --rm --net=host -v "$PWD:/mapping" openmaptiles/postserve /mapping/myfile.sql
#
CMD ["/mapping/mvt/maketile_prep.sql"]
