#!/bin/sh

docker create \
  --name planex-persist \
  -v /var/cache/mock \
  -v /var/cache/yum \
  xenserver/planex:latest /bin/true

# Fill in volumes automatically from the pins file
# Chicken and egg - need to fill it in when pinning as well
docker run \
  --privileged \
  --rm -i -t \
  --volumes-from planex-persist \
  -v ${PWD}:/build \
  xenserver/planex:latest "$*"
