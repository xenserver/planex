%define branch trunk
Summary: blktap user space utilities
Name: blktap
Version: 3.3.0
Release: xs.1
License: BSD
Group: System/Hypervisor
URL: https://github.com/xapi-project/blktap
Patch0: %{name}-CA-211529-Corrected-tapdisk-stats-definitions
Patch1: %{name}-CP-18192-Removed-code-for-xlvhd-thin-provisioning
Patch2: %{name}-CP-18025-Change-blktap-license-from-gplv2-to-bsd
Patch3: %{name}-CP-18025-Use-bsd-compliant-list.h
Patch4: %{name}-CP-18025-Discontinue-use-of-upstream-nbd-header-file
Patch5: %{name}-CP-18025-Use-glibc-alternative-to-page-size-macro
Patch6: %{name}-CP-18025-Remove-dependence-on-linux-log2.h
Patch7: %{name}-pull_request_187__CP-17399_fix_resource_leaking_asprintf
Patch8: %{name}-pull_request_188__introduce_a_new_block_backend_called_ntnx
Patch9: %{name}-pull_request_190__ca-219462__remove_lock.h_and_lock.c
Patch10: %{name}-pull_request_191__CA-220042_sigact.sa_mask_is_not_initialized_CID-5755
Patch11: %{name}-pull_request_192__CA-220041_blkif_used_after_freed_CID-57556
Patch12: %{name}-pull_request_193__CA-220000_memory_leak_from_variable_path_CID-57593
Patch13: %{name}-pull_request_194__CA-220002_resource_leak_for_memory_allocated_to_pname_CID-57549
Patch14: %{name}-pull_request_195__CA-220003_Resource_leak_for_memory_allocated_to_target_CID-57413
Patch15: %{name}-pull_request_186__CA-215080_CID-63812_Uninitialized_scalar_variable
Patch16: %{name}-pull_request_196__ca-215084__bug_fixes_in_lvm-util.c
Patch17: %{name}-pull_request_198__ca-220226__fix_bugs_in_part-util.c
Patch18: %{name}-pull_request_199__ca-220433__replace_format_with_string_literal_in_tap-ctl-list.c
Patch19: %{name}-pull_request_200__ca-220434__return_err_instead_of_0
Patch20: %{name}-pull_request_201__ca-220436__fix_resource_leak_in_tap-ctl-list.c
Patch21: %{name}-pull_request_203__ca-220444__fix_possible_race_condition
Patch22: %{name}-pull_request_202__ca-220442__check_length_of_socket_name_before_copying
Patch23: %{name}-pull_request_206__ca-220463__ensure_string_fits_in_buffer_before_copying
Patch24: %{name}-pull_request_204__ca-220478__fix_leaked_socket_file_descriptor
Patch25: %{name}-pull_request_205__ca-220479__remove_nonsensical_checks
Patch26: %{name}-pull_request_213__ca-220518__potentially_uninitialised_variable_used
Patch27: %{name}-pull_request_208__ca-220482__check_return_value_of_fwrite
Patch28: %{name}-pull_request_212_1__cid-11258_unchecked_return_value_from_library
Patch29: %{name}-pull_request_212_2__cid-28562_dereference_null_return_value
Patch30: %{name}-pull_request_212_3__cid-28703_destination_buffer_too_small
Patch31: %{name}-pull_request_212_4__cid-28739_double_close
Patch32: %{name}-pull_request_212_5__cid-62178_cid-57555_read_or_write_to_pointer_after_free
Patch33: %{name}-pull_request_197__cp-18757__refactor_the_way_we_use_ctx_fd_CID-28676
Patch34: %{name}-pull_request_207__ca-220481__fixes_in_tap_ctl_stats_fwrite
Patch35: %{name}-pull_request_210__ca-215114__resource_leak_in_vhd_util_coalesce_open_output
Patch36: %{name}-pull_request_214__ca-216250__fix_resource_leak
Patch37: %{name}-pull_request_217__ca-221814__fix_resource_leak_in_vhdi_create
Patch38: %{name}-pull_request_218__ca-221864__fix_bugs_in_vhd_journal_read_locators
Patch39: %{name}-pull_request_220__ca-222003__fix_null_dereference_bug
Patch40: %{name}-pull_request_221__ca-216249__check_length_of_socket_name_before_copying
Patch41: %{name}-pull_request_222__ca-222077__fix_bugs_in_td_fdreceiver_start
Patch42: %{name}-pull_request_223__ca-222139__resource_leak_in_tap_ctl_allocate_device
Patch43: %{name}-pull_request_225__ca-222242__memset_1_byte_instead_of_4
Patch44: %{name}-pull_request_226__ca-222244__fix_resource_leaks_in_vhd_shift_metadata
Patch45: %{name}-pull_request_228__CA-222124_Handle_race_condition_in_tap-ctl_spawn
Patch46: %{name}-pull_request_229__ca-223652__add_delay_to_reduce_number_of_syslog_messages
Patch47: %{name}-pull_request_231__cp-14449__fix_version_and_release_tag_in_specfile
Patch48: %{name}-pull_request_219__ca-221904__vhd_create_einval_report_errors
Patch49: %{name}-add_coverity_model.c_to_support_asprintf
Patch50: %{name}-pull_request_230__CA-225067-tap_ctl_-spawn-create-move-tapdisk-to-cgro
Source0: http://hg.uk.xensource.com/git/carbon/%{branch}/blktap.git/snapshot/refs/tags/v%{version}#/%{name}-%{version}.tar.gz

BuildRoot: %{_tmppath}/%{name}-%{release}-buildroot
Obsoletes: xen-blktap
BuildRequires: e2fsprogs-devel, libaio-devel, systemd, autogen, autoconf, automake, libtool, libuuid-devel
BuildRequires: xen-devel, kernel-devel, xen-dom0-libs-devel, zlib-devel, xen-libs-devel
Requires(post): systemd
Requires(preun): systemd
Requires(postun): systemd

%description
Blktap creates kernel block devices which realize I/O requests to
processes implementing virtual hard disk images entirely in user
space.

Typical disk images may be implemented as files, in memory, or
stored on other hosts across the network. The image drivers included
with tapdisk can map disk I/O to sparse file images accessed through
Linux DIO/AIO and VHD images with snapshot functionality.

This packages includes the control utilities needed to create
destroy and manipulate devices ('tap-ctl'), the 'tapdisk' driver
program to perform tap devices I/O, and a number of image drivers.

%package devel
Summary: BlkTap Development Headers and Libraries
Requires: blktap = %{version}
Group: Development/Libraries
Obsoletes: xen-blktap

%description devel
Blktap and VHD development files.

%prep
%setup -q -n %{name}-v%{version}
patch -p1 < mk/blktap-udev-ignore-tapdevs.patch
%autosetup -T -D -p1

%build
sh autogen.sh
%configure
%{?cov_wrap} make

%install
rm -rf %{buildroot}
make install DESTDIR=%{buildroot}
mkdir -p %{buildroot}%{_localstatedir}/log/blktap

%files
%defattr(-,root,root,-)
%doc
%{_libdir}/*.so
%{_libdir}/*.so.*
%{_bindir}/vhd-util
%{_bindir}/vhd-update
%{_bindir}/vhd-index
%{_bindir}/tapback
%{_bindir}/cpumond
%{_sbindir}/lvm-util
%{_sbindir}/tap-ctl
%{_sbindir}/td-util
%{_sbindir}/td-rated
%{_sbindir}/part-util
%{_sbindir}/vhdpartx
%{_libexecdir}/tapdisk
%{_sysconfdir}/udev/rules.d/blktap.rules
%{_sysconfdir}/logrotate.d/blktap
%{_sysconfdir}/xensource/bugtool/tapdisk-logs.xml
%{_sysconfdir}/xensource/bugtool/tapdisk-logs/description.xml
%{_localstatedir}/log/blktap
%{_unitdir}/tapback.service
%{_unitdir}/cpumond.service

%files devel
%defattr(-,root,root,-)
%doc
%{_libdir}/*.a
%{_libdir}/*.la
%{_includedir}/vhd/*
%{_includedir}/blktap/*

%post
%systemd_post tapback.service
%systemd_post cpumond.service

%preun
%systemd_preun tapback.service
%systemd_preun cpumond.service

%postun
%systemd_postun tapback.service
%systemd_postun cpumond.service

%changelog
