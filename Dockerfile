FROM centos:7.2.1511
MAINTAINER Euan Harris <euan.harris@citrix.com>
RUN yum -y install \
  epel-release \
  yum-utils

# Copy spec file and install dependencies.
# The spec file rarely changes, so the dependency installation layers
# can be cached even if the planex code needs to be rebuilt.
WORKDIR /usr/src
COPY planex.spec planex/
RUN yum-builddep -y planex/planex.spec
RUN awk '/^Requires:/ { print $2 }' planex/planex.spec | xargs yum -y install
RUN useradd build --groups mock,wheel --home-dir /build

# Copy source, build and install it.
COPY . planex/
WORKDIR /usr/src/planex
RUN python setup.py build
RUN python setup.py install

WORKDIR /build
COPY docker/entry.sh /entry.sh
ENTRYPOINT ["bash", "/entry.sh"]
