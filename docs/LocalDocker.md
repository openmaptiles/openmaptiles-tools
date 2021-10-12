## Connect local `openmaptiles-tools` with local `openmaptiles`:

Very helpful for contributors who want to develop and test `openmaptiles-tools` with `openmaptiles` together.

### Change docker path in `docker-compose.yml`

In the `openmaptiles` project the `Dockerfile` path in the file [`docker-compose.yml`](https://github.com/openmaptiles/openmaptiles/blob/master/docker-compose.yml#L30) needs to be changed.

Replace `image` with `build` and add the path of `openmaptiles-tools` to `context` (can be a relative path):

Old:
```
  openmaptiles-tools:
    image: "openmaptiles/openmaptiles-tools:${TOOLS_VERSION}"
    env_file: .env
```
New:
```
  openmaptiles-tools:
    #image: "openmaptiles/openmaptiles-tools:${TOOLS_VERSION}" #comment
    build:
      context: ../openmaptiles-tools
      dockerfile: Dockerfile
    env_file: .env
```

With the next run of a script that needs `openmaptiles-tools` it uses the local project and builds a docker image automatically.

### Generate new docker image after changes:

For every change in `openmaptiles-tools` the docker image needs to be generated new.

First the old docker image needs to be removed:
```
# list all docker images:
docker images

# search for the openmaptiles-tools image and get the `IMAGE ID`

# Remove the docker image
docker rmi IMAGE_ID --force
```

or simply use:
```
docker rmi $(docker images | awk '$1 ~ /openmaptiles-tools/ { print $3}') --force
```

With the next run of a script that needs `openmaptiles-tools` it uses the local project and builds a docker image automatically again.
