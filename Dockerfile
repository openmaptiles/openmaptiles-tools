FROM python:3.6

RUN apt-get update \
    && apt-get install  -y --no-install-recommends \
        graphviz \
        sqlite3 \
    && rm -rf /var/lib/apt/lists/

WORKDIR /usr/src/app
# Copy requirements.txt first to avoid pip install on every code change
COPY ./requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mv bin/* .
ENV PATH="/usr/src/app:${PATH}"

WORKDIR /tileset
VOLUME /tileset
