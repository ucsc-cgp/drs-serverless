include ../common.mk

deploy:
	./build_deploy_config.sh
	gcloud endpoints services deploy drs-api.yml

PHONY: deploy
