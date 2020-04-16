## Creating PostgreSQL database
There are several ways to create a PostgreSQL database for OpenStreetMap data. The simplest is to run it in a Docker container on your local machine. The more involved is to use one of the cloud providers, such as Google Cloud.
 
All of the examples here use these environment variables (the values can be changed):

```bash
export POSTGRES_DB=openmaptiles
export POSTGRES_USER=openmaptiles
export POSTGRES_PASSWORD=openmaptiles
``` 

Once PostgreSQL is running, you can test connection with

```bash
PGPASSWORD="$POSTGRES_PASSWORD" psql -h localhost --user "$POSTGRES_USER" "$POSTGRES_DB"
```

### Docker Image

```bash
export POSTGRES_DB=openmaptiles         # Database name, user, and password will be
export POSTGRES_USER=openmaptiles       # created automatically based on these values.
export POSTGRES_PASSWORD=openmaptiles
export DATA_DIR=$PWD/pgdata             # store data in the current dir/pgdata

mkdir -p $DATA_DIR      # Ensure the data dir exists
docker run \
  --rm                 `# Delete this container on exit` \
  -it                  `# Run container with a terminal` \
  -p 5432:5432         `# Allow external access to the port 5432`  \
  -e POSTGRES_DB       `# On first run, create this database`      \
  -e POSTGRES_USER     `# On first run, create this user/password` \
  -e POSTGRES_PASSWORD \
  -v $DATA_DIR:/var/lib/postgresql/data  `# Use current directory/pgdata to store PostgreSQL data` \
   openmaptiles/postgis:latest             `# Use the latest OpenMapTiles postgis image` \
   postgres
```

For the PostgreSQL versions 11+, make sure to use `postgres -c 'jit=off'` as the last line to run postgres with disabled JIT due to a bug making MVT queries run very slow.


### Google Cloud (GCP)

To run PostgreSQL in Google cloud, you need install `gcloud` utility, and login into your Google account. You will need to set up a firewall rule to enable inbound access. 

Additional notes:
* See [GCP machine types](https://cloud.google.com/compute/docs/machine-types) for the `MACHINE_TYPE` setting. The `n1-highmem-2` uses an older 2-CPU machine with max memory. Full planet should use a bigger machine.
* The `VM_DISK_SIZE` should fit OS + Apps + Data. Use ~700GB for the whole planet.
* See [gcp startup script](gcp_startup.sh)

#### Set required env variables

```bash
export GOOGLE_PROJECT_ID=<my_project>  # Set to your GCP project name 
export GOOGLE_ZONE_NAME=us-central1-c  # Which zone to use for the new VM 
export PG_VM_NAME=pg1                  # Name of the VM to create

export VM_DISK_SIZE=15GB               # VM disk size
export MACHINE_TYPE=n1-standard-1      # Type of GCP VM to create
export PG_VERSION=12                   # PostgreSQL version

export POSTGRES_DB=openmaptiles        # Database name, user, and password will be
export POSTGRES_USER=openmaptiles      # created automatically based on these values.
export POSTGRES_PASSWORD=openmaptiles
```

#### Firewall rule
Create a firewall rule for VM instances tagged with "pg" to allow inbound PostgreSQL connections, but only from the local project network (not public).

```bash
gcloud compute firewall-rules create allow-postgres \
    --description "Allow private PostgreSQL traffic on TCP port 5432" \
    --project $GOOGLE_PROJECT_ID \
    --allow tcp:5432 \
    --direction INGRESS \
    --source-ranges 10.0.0.0/8 \
    --target-tags pg
```

#### Create Virtual Machine
Create a new virtual machine and run startup script on it.
```bash
gcloud compute instances \
    create $PG_VM_NAME             `# Create new VM with this name` \
    --project $GOOGLE_PROJECT_ID   `# in this GCP project` \
    --zone $GOOGLE_ZONE_NAME       `# and in this VM zone` \
    --image-family debian-10       `# use latest Debian-10 base image` \
    --image-project debian-cloud   `# ` \
    --boot-disk-size $VM_DISK_SIZE `# Enough to fit OS+apps+data` \
    --boot-disk-type pd-ssd        `# Use faster SSD disks (more expensive)` \
    --machine-type=$MACHINE_TYPE   `# Specify machine hardware` \
    --tags=pg                      `# Use firewall rule from above` \
                                   `# Set boot script and required metadata` \
    --metadata-from-file startup-script=gcp_startup.sh \
    --metadata pg_version=$PG_VERSION,pg_database=$POSTGRES_DB,pg_user=$POSTGRES_USER,pg_password=$POSTGRES_PASSWORD
```

#### Login and Verify
Login into the newly created VM: 
```bash
gcloud compute ssh --project $GOOGLE_PROJECT_ID $PG_VM_NAME --zone=$GOOGLE_ZONE_NAME
```

Observe how the Postgres DB is being initialized by watching the output from the startup script. This command will show the last 1000 lines, and will wait for any new log lines. Use Ctrl+C to stop viewing.

```bash
sudo tail -f -n 1000 /var/log/syslog | grep 'GCEMetadataScripts:'
```

Connect to the newly initialized database by using postrges root account (from VM):

```bash
sudo -u postgres psql openmaptiles
```

You can also connect to the PostgreSQL server remotely from your local machine by using ssh port-forwarding. Run this command instead of (or in addition to) the regular ssh.

```bash
# From your local machine:
gcloud compute ssh --project $GOOGLE_PROJECT_ID $PG_VM_NAME --zone=$GOOGLE_ZONE_NAME -- -L 5432:localhost:5432

# From another terminal window on your local machine.
# Make sure these env vars are set.
PGPASSWORD="$POSTGRES_PASSWORD" psql -h localhost --user "$POSTGRES_USER" "$POSTGRES_DB"
```
