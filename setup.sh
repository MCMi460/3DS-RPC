#!/bin/bash
#
# This file will use my forks of the following repositories for functionality
# The reason for this is purely because of anynet's reliance upon netifaces
# which always fails with building on my aarch64 server. If you are using
# an architecture that may not support netifaces, please feel free to
# use this shell script.
#

if [ -d ./venv/ ]
then
  rm -rf ./venv/
fi
python3 -m venv venv
source venv/bin/activate
git clone https://github.com/MCMi460/anynet -b w/o-netifaces
cd anynet && python -m pip install . && cd ..
rm -rf anynet
git clone https://github.com/MCMi460/NintendoClients -b update-anynet
cd NintendoClients && python -m pip install . && cd ..
rm -rf NintendoClients
python -m pip install -r requirements.txt
