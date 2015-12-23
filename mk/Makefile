include $(B_BASE)/common.mk
include $(B_BASE)/rpmbuild.mk

#### Build-system boilerplate above ####
.PHONY: build buildrpms
build: $(MY_SOURCES)/MANIFEST

conf_dir:
	# Figure out which set of spec files we're building based on 'COMPONENT'
	./get_config_dir.py
	$(eval CONFIG_DIR=$(shell ./get_config_dir.py))

srpmutil:
	make -C ../srpmutil

buildrpms: conf_dir srpmutil
	echo "Installing latest planex"
	@cd .. && python setup.py install
	echo confdir $(CONFIG_DIR)
	chown -R root.root $(CONFIG_DIR)/*
	planex-configure --config-dir=$(CONFIG_DIR) --use-distfiles
	rm -rf planex-build-root/RPMS
	mkdir planex-build-root/RPMS
	cp /distfiles/centos5/buildsys-build* planex-build-root/RPMS
	createrepo planex-build-root/RPMS/
	touch /etc/hosts
	planex-build --xs-build-sys --use-mock
	planex-install $(CONFIG_DIR) $(MY_MAIN_PACKAGES)
	cp -r ./planex-build-root/RPMS $(MY_OUTPUT_DIR)
	rm -rf $(MY_OUTPUT_DIR)/RPMS/repodata
	cp -r ./planex-build-root/SRPMS $(MY_OUTPUT_DIR)

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
