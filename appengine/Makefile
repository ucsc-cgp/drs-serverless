include ../common.mk

deploy:
	cp -R ../drs ../requirements.txt .
	./build_deploy_config.sh

bar:
	gcloud app deploy \
		-v ${DRS_APPENGINE_SERVICE_VERSION} \
		--quiet \
		--project ${GCP_PROJECT} app.yaml

foo:
	@gcloud app versions describe \
		${DRS_APPENGINE_SERVICE_VERSION} \
		--service=${DRS_APPENGINE_SERVICE_NAME} \
		--format json \
		| jq -r .versionUrl

clean:
	git checkout -- app.yaml

.PHONY: deploy clean
