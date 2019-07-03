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
RUN mv bin/* . && \
    rm -rf bin && \
    rm requirements.txt

ENV PATH="/usr/src/app:${PATH}"

WORKDIR /tileset
VOLUME /tileset

# In case there are no parameters, print a list of available scripts
CMD echo "*******************************************************************" && \
    echo "  Please specify a script to run. Here are the available scripts." && \
    echo "  Use script name with --help to get more information." && \
    echo "  Use 'bash' to start a shell inside the tools container." && \
    echo "*******************************************************************" && \
    find /usr/src/app -maxdepth 1 -executable -type f -printf " * %f\n"
