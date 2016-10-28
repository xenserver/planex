# This prevents vhostmd-debuginfo-%{version}-%{release}.rpm being built
%define debug_packages	%{nil}
%define debug_package %{nil}

Name:           vhostmd
Version:        0.4
Release:        xs28
Epoch:          0
Summary:        Virtual Host Metrics Daemon

Group:          Application/Productivity
License:        GPL
URL:            http://www.novell.com
Source0:        https://repo.citrite.net/xs-local-contrib/vhostmd/%{name}-%{version}.tar.gz
Source1:        xe-vhostmd
patch0:         patch-etc_init.d_vhostmd
patch1:         patch-fix-enable-xenctrl-configure-opt
patch2:         patch-etc_vhostmd_vhostmd.conf
patch3:         patch-xen-4.1
patch4:         de-perl.patch
patch5:         patch-remove-xs-h
patch6:         configure-dlopen.patch
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}
BuildRequires:	libtool, autoconf, automake, libxml2-devel, xen-dom0-devel, xen-libs-devel

%description
vhostmd provides a "metrics communication channel" between a host and
its hosted virtual machines, allowing limited introspection of host
resource usage from within virtual machines.  This functionality may be
useful in hosting environments, giving virtual machine administrators
a limited view of host resource consumption - potentially explaining a
performance degradation within the virtual machine.

vhostmd will periodically write metrics to a disk.  The metrics to
write, how often, and where to write them are all adjustable via the
/etc/vhostmd/vhostmd.conf configuration file.  The disk can then be
surfaced read-only to virtual machines using tools provided by the 
virtualization platform of the host.

%prep
%setup -q -n %{name}-%{version}
%patch4 -p1 -b .de-perl
%patch0 -p1 -b .xs-init-script
%patch1 -p1 -b .xs-fix-configure-opt
%patch2 -p1 -b .xs-vhostmd-conf
%patch3 -p1 -b .xs-xen-4.1
%patch5 -p1 -b .xs-remove-xs-h
%patch6 -p0 -b .xs-configure-dlopen

%build
sh autogen.sh
%configure --enable-xenctrl
make %{?_smp_mflags}

%install
rm -rf %{buildroot}
make install DESTDIR=%{buildroot}
install -m 755 %{_sourcedir}/xe-vhostmd %{buildroot}/usr/sbin

%clean
rm -rf %{buildroot} 

%preun
if [ "$1" = 0 ] ; then
  chkconfig --del vhostmd
fi

%files 
%defattr(-,root,root,-)
/usr/sbin/vhostmd
/usr/sbin/vm-dump-metrics
/usr/sbin/xe-vhostmd
%{_mandir}/man1/vm-dump-metrics.1.gz
%{_mandir}/man8/vhostmd.8.gz
%{_libdir}/libmetrics.so.0.0.0
%{_libdir}/libmetrics.so.0
%{_libdir}/libmetrics.so
%{_libdir}/libmetrics.a
%{_libdir}/libmetrics.la
/usr/include/vhostmd/libmetrics.h
/usr/share/vhostmd/scripts/pagerate.py
/usr/share/vhostmd/scripts/pagerate.pyc
/usr/share/vhostmd/scripts/pagerate.pyo
/usr/share/doc/vhostmd/README
/usr/share/doc/vhostmd/mdisk.xml
/usr/share/doc/vhostmd/vhostmd.dtd
/usr/share/doc/vhostmd/vhostmd.xml
/usr/share/doc/vhostmd/metric.dtd
%config /etc/init.d/vhostmd
%config /etc/vhostmd/vhostmd.conf
%config /etc/vhostmd/vhostmd.dtd
%config /etc/vhostmd/metric.dtd

%changelog
* Wed May 02 2012 <support@citrix.com> - added xe-vhostmd
* Thu Nov 03 2011 <support@citrix.com> - XenServer vhostmd package
- removed post-install section: do not start vhostmd automatically by default.
- preun is no longer run on upgrade, only on uninstalling all versions.
* Wed Apr 28 2010 <support@citrix.com> - XenServer vhostmd package
- updated config following testing at SAP
* Tue Mar 10 2009 <support@citrix.com> - XenServer vhostmd package
- initial version
