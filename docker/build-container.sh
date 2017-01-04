#!/bin/sh -xe

docker build -t planex-master --force-rm=true -f ../Dockerfile ..
