#!/bin/sh

docker create \
  --name planex-persist \
  -v /var/cache/mock \
  -v /var/cache/yum \
  planex-release:0.7.3 /bin/true

# Fill in volumes automatically from the pins file
# Chicken and egg - need to fill it in when pinning as well
docker run \
  --privileged \
  --rm -i -t \
  --volumes-from planex-persist \
  -v ${PWD}:/build \
  planex-release:0.7.3 "$*"
