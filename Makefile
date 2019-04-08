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

deploy: deploy-endpoints deploy-appengine

deploy-endpoints:
	$(MAKE) -C endpoints

deploy-appengine:
	$(MAKE) -C appengine

clean:
	git clean -Xdf appengine endpoints
	git checkout $$(git status --porcelain appengine/app.yaml | awk '{print $$2}')

.PHONY: all lint mypy $(tests) test deploy deploy-endpoints deploy-appengine clean
