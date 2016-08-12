#!/bin/sh -xe

docker build -t planex-master --force-rm=true -f ../Dockerfile ..
docker build -t planex-release:0.8.0 --force-rm=true -f Dockerfile.release .
docker build -t planex-unstable --force-rm=true -f Dockerfile.unstable .
