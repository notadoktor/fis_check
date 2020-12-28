.EXPORT_ALL_VARIABLES:
PIPENV_VENV_IN_PROJECT = 1
USER_BIN ?= $(HOME)/bin
FIS_SCRIPT = $(USER_BIN)/fis_check

install: install_deps install_script ## Installs dependencies, creates wrapper script at $(USER_BIN)/fis_script

install_deps:
	pipenv sync --dev

install_script:
	mkdir -p $(USER_BIN)
	echo $(firstword $(MAKEFILE_LIST))
	perl -pe "s|FIS_ROOT|$$(dirname $(realpath $(firstword $(MAKEFILE_LIST))))|" bin/fis_check > $(FIS_SCRIPT)
	chmod +x $(FIS_SCRIPT)

.PHONY: help
help:
	grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
