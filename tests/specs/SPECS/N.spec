# -*- rpm-spec -*-

%define repo_name xe-guest-utilities

Summary: VM Monitoring Scripts
Name: N
Version: 7.9.0
Release: 1
License: BSD
Group: Xen
URL: http://www.citrix.com
Vendor:  citrix
Source0: https://github.com/xenserver/%{repo_name}/archive/v%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
BuildRequires: wget
Obsoletes: xengmond


%description
Scripts for monitoring VM

Writes distribution version information and IP address to XenStore.

%package xenstore
Summary: VM XenStore utilities
Group: Xen
%description xenstore
Utilities for interacting with XenStore from with a Xen VM

%prep
%autosetup -p1 -n %{repo_name}-%{version}

%build
rm -rf %{buildroot}
gopath=$(pwd)/gotools
goroot=$gopath/go
go_tool_name=go1.8.linux-amd64.tar.gz
mkdir -p obj $gopath
wget -O $gopath/$go_tool_name https://redirector.gvt1.com/edgedl/go/$go_tool_name
tar -xzvf $gopath/$go_tool_name -C $gopath --overwrite
GOROOT=$goroot $goroot/bin/go build -a -x -ldflags="-s -w" -o obj/xe-daemon xe-daemon/xe-daemon.go
GOROOT=$goroot $goroot/bin/go build -a -x -ldflags="-s -w" -o obj/xenstore xenstore/xenstore.go


%install
mkdir -p %{buildroot}/usr/sbin/
mkdir -p %{buildroot}/usr/share/doc/%{name}-%{version}/examples/
mkdir -p %{buildroot}/etc/init.d
mkdir -p %{buildroot}/etc/udev/rules.d

cp mk/xe-linux-distribution %{buildroot}/usr/sbin/xe-linux-distribution
chmod 755 %{buildroot}/usr/sbin/xe-linux-distribution

cp mk/xe-linux-distribution.init %{buildroot}/etc/init.d/xe-linux-distribution
chmod 755 %{buildroot}/etc/init.d/xe-linux-distribution

cp obj/xe-daemon %{buildroot}/usr/sbin/xe-daemon
chmod 755 %{buildroot}/usr/sbin/xe-daemon

cp mk/Citrix.repo  %{buildroot}/usr/share/doc/%{name}-%{version}/examples/

install -d %{buildroot}/usr/bin/
install -m 755 obj/xenstore %{buildroot}/usr/bin/xenstore
ln -s /usr/bin/xenstore %{buildroot}/usr/bin/xenstore-read
ln -s /usr/bin/xenstore %{buildroot}/usr/bin/xenstore-write
ln -s /usr/bin/xenstore %{buildroot}/usr/bin/xenstore-exists
ln -s /usr/bin/xenstore %{buildroot}/usr/bin/xenstore-rm

cp mk/xen-vcpu-hotplug.rules %{buildroot}/etc/udev/rules.d/z10-xen-vcpu-hotplug.rules

cp LICENSE  %{buildroot}/usr/share/doc/%{name}-%{version}/

mkdir -p %{buildroot}/usr/share/doc/%{name}-xenstore-%{version}
cp LICENSE  %{buildroot}/usr/share/doc/%{name}-xenstore-%{version}/

%clean
rm -rf %{buildroot}

%post
/sbin/chkconfig --add xe-linux-distribution >/dev/null
[ -n "${EXTERNAL_P2V}" ] || service xe-linux-distribution start >/dev/null 2>&1

eval $(/usr/sbin/xe-linux-distribution)

if [ -d /etc/yum.repos.d ] && [ -n "${os_distro}" ] && [ -n "${os_majorver}" ] ; then
    distro="${os_distro}${os_majorver}x"
    case "${distro}" in
    rhel4x|centos4x)
        if [ -f /etc/yum.repos.d/XenSource.repo ] ; then
            rm -f /etc/yum.repos.d/XenSource.repo # contains deprecated urls
        fi
        sed -e "s/\^DISTRO\^/${distro}/g" \
            < /usr/share/doc/%{name}-%{version}/examples/Citrix.repo \
            > /etc/yum.repos.d/Citrix.repo
        ;;
    rhel3x|rhel5x|centos5x|oracle5x) # No vendor kernel any more. Remove Citrix.repo
        if [ -f /etc/yum.repos.d/Citrix.repo ] ; then
            rm -f /etc/yum.repos.d/Citrix.repo
        fi
        ;;
    *) ;;
    esac
fi

%preun
if [ $1 -eq 0 ] ; then
    service xe-linux-distribution stop >/dev/null 2>&1
    /sbin/chkconfig --del xe-linux-distribution >/dev/null
    rm -f /etc/yum.repos.d/Citrix.repo || /bin/true
fi

%files 
%defattr(-,root,root,-)
/usr/sbin/xe-linux-distribution
/etc/init.d/xe-linux-distribution
/usr/sbin/xe-daemon
/etc/udev/rules.d/z10-xen-vcpu-hotplug.rules
/usr/share/doc/%{name}-%{version}/examples/Citrix.repo
/usr/share/doc/%{name}-%{version}/LICENSE

%files xenstore
%defattr(-,root,root,-)
/usr/bin/xenstore-*
/usr/bin/xenstore
/usr/share/doc/%{name}-xenstore-%{version}/LICENSE

%changelog
* Tue Nov 28 2017  <citrix.com>
- Xen monitor scripts
