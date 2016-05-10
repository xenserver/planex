#!/bin/sh -xe

docker build -t planex-release:0.7.3 --force-rm=true -f Dockerfile.release .
docker build -t planex-master --force-rm=true -f Dockerfile.master .
docker build -t planex-unstable --force-rm=true -f Dockerfile.unstable .
