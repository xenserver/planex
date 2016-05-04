#!/bin/sh -xe

echo $@
EXTUID=`stat -c %u /build`
EXTGID=`stat -c %g /build`

# Change 'build' UID in the container to match the owner of the
# build directory, so that built packages will have the correct
# owner outside the container.
usermod --non-unique -u $EXTUID build
groupmod --non-unique -g $EXTGID build
su - build -c "$*"
