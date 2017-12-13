FROM centos:7.4.1708
MAINTAINER Euan Harris <euan.harris@citrix.com>

# yum-plugin-ovl works around problems on OverlayFS-backed containers:
#   https://github.com/docker/docker/issues/10180
RUN yum -y install yum-plugin-ovl \
  && yum clean all

# Install basic prerequisites for building planex
RUN yum -y install \
  epel-release \
  yum-utils \
  && yum clean all

# Install sudo and preconfigure the sudoers file for the build user
RUN yum -y install sudo \
  && yum clean all \
  && echo 'build ALL=(ALL:ALL) NOPASSWD:ALL' >> /etc/sudoers \
  && sed -i.bak 's/^Defaults.*requiretty//g' /etc/sudoers

# Copy spec file and install dependencies.
# The spec file rarely changes, so the dependency installation layers
# can be cached even if the planex code needs to be rebuilt.
WORKDIR /usr/src
COPY planex.spec planex/
RUN yum-builddep -y planex/planex.spec \
  && awk '/^Requires:/ { print $2 }' planex/planex.spec | xargs yum -y install \
  && yum clean all \
  && mkdir /build

# Copy source, build and install it.
COPY . planex/
WORKDIR /usr/src/planex
RUN python setup.py build \
  && python setup.py install

WORKDIR /build
COPY docker/entry /entry
ENTRYPOINT ["/entry"]
