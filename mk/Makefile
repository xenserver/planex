include $(B_BASE)/common.mk
include $(B_BASE)/rpmbuild.mk

# Figure out which set of spec files we're building based on 'COMPONENT'
CONFIG_DIR=$(shell ./get_config_dir.py)

#### Build-system boilerplate above ####
.PHONY: build buildrpms
build: $(MY_SOURCES)/MANIFEST

buildrpms:
	echo "%_topdir /repos/planex" > .rpmmacros
	echo confdir $(CONFIG_DIR)
	chown -R root.root $(CONFIG_DIR)/*
	@cd .. && ./configure.py $(CONFIG_DIR)
	@cd .. && ./build.py
	@cd .. && ./install.py $(CONFIG_DIR) $(MY_MAIN_PACKAGES)
	cp -r ../RPMS $(MY_OUTPUT_DIR)
	cp -r ../SRPMS $(MY_OUTPUT_DIR)
	rpm -Uvh --force --nodeps ../RPMS/*.rpm

#### Build-system boilerplate below ####

$(MY_SOURCES)/MANIFEST: $(MY_SOURCES_DIRSTAMP) buildrpms
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
