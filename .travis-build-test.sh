set -uex

export DOCKER_IMAGE="planex/buildtest"
export DOCKER_CMD="make"
export TEST_REPO="$PWD/tests/specs"
export TEST_CMD='docker run --privileged --rm -itv $TEST_REPO:/build $DOCKER_IMAGE /bin/bash -c "$DOCKER_CMD"'

docker build -t planex/buildtest --force-rm=true .
eval ${TEST_CMD}
