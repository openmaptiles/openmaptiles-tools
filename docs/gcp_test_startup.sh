#!/usr/bin/env bash
set -euo pipefail

if (( $(id -u) != 0 )); then
  echo "***************************************************"
  echo "***  FATAL:  This script should be ran as ROOT  ***"
  echo "***************************************************"
  exit 1
fi


USER_LOGIN_FILE="/etc/profile.d/init-omt.sh"


if [[ ! -f "${USER_LOGIN_FILE}" ]]; then
  echo "************ First time initialization **************"

  cat <<EOF | tee "$USER_LOGIN_FILE"
# This script is executes every time a user logs in

if [[ ! -d "~/openmaptiles" ]]; then
  echo "***** First login (~/openmaptiles/ does not exist) *****"
  echo ""
  git clone https://github.com/openmaptiles/openmaptiles.git
  echo ""
  git clone https://github.com/openmaptiles/openmaptiles-tools.git
  echo ""
fi

cd openmaptiles
docker ps || echo -e "Docker is not yet installed, please wait for the boot script to complete"
echo "To see the progress of the boot script, use"
echo "  sudo tail -f -n 1000 /var/log/syslog | grep 'startup-script:'"
EOF

  echo "------------- Installing required packages..."
  DEBIAN_FRONTEND=noninteractive apt-get update -qq
  DEBIAN_FRONTEND=noninteractive apt-get install -y docker.io docker-compose htop linux-tools-common make
  echo "------------- Starting docker daemon and allowing all users to access it"
  service docker start
  chmod 666 /var/run/docker.sock
  echo "------------- Done with first time setup"

else
  echo "Not the first boot, skipping package installation"
fi  # end of the code that only runs on the first startup
