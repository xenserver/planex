#!/bin/sh -xe

docker build -t planex-release:0.7.3 --force-rm=true -f Dockerfile.release .
