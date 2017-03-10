#!/bin/sh

set -xe

echo $@
EXTUID=`stat -c %u /build`
EXTGID=`stat -c %g /build`

# Create 'build' user in the container to match the owner of the
# build directory, so that built packages will have the correct
# owner outside the container.
groupadd build --gid $EXTGID      \
               --non-unique
useradd build --groups mock,wheel \
              --home-dir /build   \
              --uid $EXTUID       \
              --gid $EXTGID       \
              --no-create-home    \
              --non-unique

exec sudo -u build -i SSH_AUTH_SOCK=$SSH_AUTH_SOCK $@
