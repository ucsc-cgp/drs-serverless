include common.mk
MODULES=drs tests

all: test

lint:
	flake8 $(MODULES)

# TODO: remove --no-strict-optional when the codebase is ready for it.
mypy:
	mypy --ignore-missing-imports --no-strict-optional $(MODULES)

tests:=$(wildcard tests/test_*.py)

test: $(tests)
	coverage combine
	rm -f .coverage.*

# A pattern rule that runs a single test script
$(tests): %.py : mypy lint
	coverage run -p --source=drs $*.py $(DSS_UNITTEST_OPTS)

create:
	gcloud app create --project=${GCP_PROJECT} --region=${GCP_DEFAULT_REGION}

deploy: deploy-cloud-endpoints deploy-appengine

deploy-cloud-endpoints: drs-api.yml
	gcloud endpoints services deploy drs-api.yml

deploy-appengine: app.yaml
	gcloud app deploy \
		-v ${DRS_APPENGINE_SERVICE_VERSION} \
		--quiet \
		--project ${GCP_PROJECT} app.yaml
	@gcloud app versions describe \
		${DRS_APPENGINE_SERVICE_VERSION} \
		--service=${DRS_APPENGINE_SERVICE_NAME} \
		--format json \
		| jq -r .versionUrl

drs-api.yml:
	cat drs-api.yml.in | yq . | jq --arg host "${GCP_PROJECT}.appspot.com" '.host=$$host' | yq -y . | sponge drs-api.yml

app.yaml:
	cat app.yaml.in | yq . | jq --arg service ${DRS_APPENGINE_SERVICE_NAME} '.service=$$service' | yq -y . | sponge app.yaml

clean:
	rm -rf app.yaml drs-api.yml
	git clean -Xdf $(MODULES)
	git checkout $$(git status --porcelain {chalice,daemons/*}/.chalice/config.json | awk '{print $$2}')

.PHONY: all lint mypy $(tests) test deploy deploy-cloud-endpoints deploy-appengine clean
.PHONY: drs-api.yml app.yaml
