.PHONY: all

all: mock/default.cfg mock/site-defaults.cfg mock/logging.ini

mock/%:
	@echo -n "Writing mock configuration..."
	@sed -e "s|@PWD@|$(PWD)|g" mock/default.cfg.in > mock/default.cfg
	@ln -fs /etc/mock/site-defaults.cfg mock/
	@ln -fs /etc/mock/logging.ini mock/
	@echo "done"

include /usr/share/planex/Makefile.rules
