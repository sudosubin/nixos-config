.EXPORT_ALL_VARIABLES:
root := $(patsubst %/,%,$(dir $(realpath $(lastword $(MAKEFILE_LIST)))))
ANSIBLE_CONFIG := $(root)/ansible.cfg
PYTHONWARNINGS := ignore:Unverified HTTPS request
unexport root

ifneq (,$(wildcard $(root)/.makerc))
	include $(root)/.makerc
endif

define message
	echo "$$(tput setaf 2)$(strip $(1))$$(tput sgr 0)"
endef

.PHONY: bootstrap
bootstrap: install check play

.PHONY: install
install:
	@if [ ! -d "$(root)/.venv" ]; then \
		$(call message, Create Virtualenv); \
		/usr/bin/python3 -m venv "$(root)/.venv"; \
		printf "Done\n\n"; \
	fi

	@$(call message, Install python packages)
	@"$(root)/.venv/bin/pip" install -U wheel
	@"$(root)/.venv/bin/pip" install -U -r "$(root)/requirements.txt"
	@echo ""

	@$(call message, Install ansible collections)
	@"$(root)/.venv/bin/ansible-galaxy" collection install --upgrade \
		-r "$(root)/requirements.yml"
	@echo ""

.PHONY: check
check:
	@$(call message, Run ansible check)
	@$(root)/.venv/bin/ansible-playbook -KCD "$(root)/site.yml"

.PHONY: play
play:
	@$(call message, Run ansible play)
	@$(root)/.venv/bin/ansible-playbook -K "$(root)/site.yml"
