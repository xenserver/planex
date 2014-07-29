include $(B_BASE)/common.mk
include $(B_BASE)/rpmbuild.mk

# Figure out which set of spec files we're building based on 'COMPONENT'
CONFIG_DIR=$(shell ./get_config_dir.py)

#### Build-system boilerplate above ####
.PHONY: build buildrpms
build: $(MY_SOURCES)/MANIFEST

buildrpms:
	echo "Installing latest planex"
	@cd .. && python setup.py install
	echo confdir $(CONFIG_DIR)
	chown -R root.root $(CONFIG_DIR)/*
	rm -rf ./planex-build-root/SRPMS/*
	planex-configure --mirror_path "file:///distfiles/ocaml2/" --repos_path "/repos" $(CONFIG_DIR)
	planex-build --xs-build-sys --no-mock --external-dependencies /obj/.ext_dependencies
	cp -r ./planex-build-root/RPMS $(MY_OUTPUT_DIR)
	rm -rf $(MY_OUTPUT_DIR)/RPMS/repodata
	cp -r ./planex-build-root/SRPMS $(MY_OUTPUT_DIR)
	rpm -Uvh --force --nodeps ./planex-build-root/RPMS/*.rpm

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
	rm -rf ./planex-build-root
