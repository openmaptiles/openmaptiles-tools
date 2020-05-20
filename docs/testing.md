## Evaluating System Performance
This document describes how to set up a system for evaluating overall tile generation performance using one-system docker-based setup, i.e. in Google Cloud.

#### Prerequisites
you need install `gcloud` utility, and login into your Google account.

Additional notes:
* See [GCP machine types](https://cloud.google.com/compute/docs/machine-types) for the `MACHINE_TYPE` setting. The `n1-highmem-2` uses an older 2-CPU machine with max memory. Full planet should use a bigger machine.
* The `VM_DISK_SIZE` should fit OS + Apps + Data.
* See [gcp test script](gcp_test_startup.sh)

#### Set required env variables

```bash
export GOOGLE_PROJECT_ID=<my_project>  # Set to your GCP project name
export GOOGLE_ZONE_NAME=us-central1-c  # Which zone to use for the new VM
export TEST_VM_NAME=omt-test           # Name of the VM to create

export VM_DISK_SIZE=25GB               # VM disk size
export MACHINE_TYPE=n1-standard-1      # Type of GCP VM to create

cd openmaptiles-tools/docs             # The current dir must contain the startup script
```

#### Create Virtual Machine
Create a new virtual machine and run startup script on it.
```bash
gcloud compute instances \
    create $TEST_VM_NAME              `# Create new VM with this name` \
    --project $GOOGLE_PROJECT_ID      `# in this GCP project` \
    --zone $GOOGLE_ZONE_NAME          `# and in this VM zone` \
    --image-family ubuntu-2004-lts    `# use latest base image` \
    --image-project ubuntu-os-cloud   `# ` \
    --boot-disk-size $VM_DISK_SIZE    `# Enough to fit OS+apps+data` \
    --boot-disk-type pd-ssd           `# Use faster SSD disks (more expensive)` \
    --machine-type=$MACHINE_TYPE      `# Specify machine hardware` \
                                      `# Set boot script and required metadata` \
    --metadata-from-file startup-script=gcp_test_startup.sh
```

#### Login and Verify
Login into the newly created VM. The OpenMapTiles and OpenMapTiles-tools repos will be automatically cloned on the first login.

```bash
# SSH to the machine, and 
gcloud compute ssh --project $GOOGLE_PROJECT_ID $TEST_VM_NAME --zone=$GOOGLE_ZONE_NAME -- -L 8090:localhost:8090

# if you don't see openmaptiles files, logoff/login - the script hasn't finished yet
ls
# See if the startup script completed ok
sudo tail -f -n 1000 /var/log/syslog | grep 'startup-script:'
```

Note that the script automatically starts [tmux](https://github.com/tmux/tmux/wiki/Getting-Started) session, so in the event of disconnect your work will not be lost. 

#### Init OpenMapTiles database
Once started and docker is accessible with `docker ps` command, check out the needed git branch and create the database.

To test a pull request, go to the bottom of the PR page, click `command line instructions`, and copy/paste `step 1`.

```bash
# Create a new database that is already pre-loaded with some data
make start-db-preloaded

# **** OR **** you can start from scratch with these two commands:
# make start-db     # create new blank database
# make import-data  # import all pre-packaged data

make all            # create needed files
make bash           # Connect to tools to run commands directly

# inside tools shell:
download-osm monaco -o /import/monaco.pbf   # download some data
import-borders                     # created borders based on the data file
import-osm                         # import data file
import-wikidata openmaptiles.yaml  # import wikidata labels for mentioned data
import-sql                         # run sql files to update indexes
exit

# start postserve and view the real time results in Maputnik
# the -L ssh param above will proxy tile requests from your machine
make start-postserve
# Start monitoring postserve (stop with Ctrl+C)
docker logs openmaptiles_postserve_1  -f
# Now open https://maputnik.github.io/editor/#12.83/43.73757/7.42704
# Click `Data Sources`, and **at the very TOP** modify TileJSON URL to `http://localhost:8090`, and click the `X` in the upper right corner.
```
