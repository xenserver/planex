ifdef B_BASE
include $(B_BASE)/common.mk
include $(B_BASE)/rpmbuild.mk
REPO=$(call hg_loc,xen-dist-ocaml)
DIST=$(CARBON_DISTFILES)/ocaml
else
MY_OUTPUT_DIR ?= $(CURDIR)/output
MY_OBJ_DIR ?= $(CURDIR)/obj
REPO ?= $(CURDIR)

RPM?=rpm
RPM_SPECSDIR?=$(shell rpm --eval='%_specdir')
RPM_SRPMSDIR?=$(shell rpm --eval='%_srcrpmdir')
RPM_RPMSDIR?=$(shell rpm --eval='%_rpmdir')
RPM_SOURCESDIR?=$(shell rpm --eval='%_sourcedir')
RPMBUILD?=rpmbuild

DIST?=/data

DOMAIN0_ARCH_OPTIMIZED?=i686

%/.dirstamp:
	@mkdir -p $*
	@touch $@
endif

RPM_BINDIR=$(RPM_RPMSDIR)/$(DOMAIN0_ARCH_OPTIMIZED)

#### Build-system boilerplate above ####
.PHONY: build clean
build: srpmutil/srpmutil
	./configure.py
	./build.py


srpmutil/srpmutil:
	make -C srpmutil

clean:
	make -C srpmutil clean
	rm SPECS/*.spec
	rm SOURCES/*


#### Build-system boilerplate below ####

$(MY_SOURCES)/MANIFEST: $(MY_SOURCES_DIRSTAMP)
	@for i in $(shell /bin/ls -1 ${RPM_SRPMSDIR}); do \
		path=$(MY_OUTPUT_DIR)/SRPMS/$${i}; \
		echo -n "ocaml "; \
		$(RPM) --qf %{License} -qp $${path} | sed -e 's/ /_/g'; \
		echo " file $${path}"; \
	done > $@.tmp
	mv -f $@.tmp $@

.PHONY: clean
clean:
	rm -rf $(RPM_SRPMSDIR) $(RPM_SPECSDIR) $(RPM_SOURCESDIR) $(RPM_RPMSDIR)
	rm -f SOURCES/*.tar.gz
	rm -f SPECS/*.spec
	rm -f targets.mk
