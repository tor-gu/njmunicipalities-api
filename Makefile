export PYTHONPATH = common_layer
export AWS_SAM_STACK_NAME=NjMunicipalitiesApiDev

src_dirs := common_layer counties municipalities scripts tests

style:
	python -m isort $(src_dirs)
	python -m black --target-version py312 $(src_dirs)
	python -m flake8 --ignore E501,E203,W503 $(src_dirs)

unit_test:
	python -m pytest -sv tests/unit

integration_test:
	python -m pytest -sv tests/integration

# README.Rmd's python chunks run through reticulate and need requests and pandas;
# use the repo's virtualenv for them if there is one
ifneq ($(wildcard .venv/bin/python),)
knit: export RETICULATE_PYTHON ?= $(abspath .venv/bin/python)
endif
knit:
	Rscript -e "rmarkdown::render('README.Rmd')"

# Export DynamoDB CSVs from a tagged njmunicipalities release, e.g. make export_data REF=v1.4.0
export_data:
	@test -n "$(REF)" || (echo "Usage: make export_data REF=<njmunicipalities git ref>" && exit 1)
	Rscript scripts/export_data.R $(REF)

# Show what loading data/ would change, e.g. make load_dry_run ENV=dev
load_dry_run:
	@test "$(ENV)" = dev -o "$(ENV)" = prod || (echo "Usage: make load_dry_run ENV=dev|prod" && exit 1)
	python scripts/load_data.py --env-prefix "$(if $(filter dev,$(ENV)),dev-,)" --dry-run

# Terraform for the DynamoDB tables, e.g. make tf_plan ENV=dev, then make tf_apply ENV=dev.
# init -reconfigure each time, since each environment has its own state file.
tf_plan:
	@test "$(ENV)" = dev -o "$(ENV)" = prod || (echo "Usage: make tf_plan ENV=dev|prod" && exit 1)
	cd infra && terraform init -reconfigure -input=false -backend-config=env/$(ENV).backend.hcl
	cd infra && terraform plan -input=false -var-file=env/$(ENV).tfvars -out=$(ENV).tfplan

tf_apply:
	@test "$(ENV)" = dev -o "$(ENV)" = prod || (echo "Usage: make tf_apply ENV=dev|prod" && exit 1)
	@test -f infra/$(ENV).tfplan || (echo "No infra/$(ENV).tfplan; run make tf_plan ENV=$(ENV) first" && exit 1)
	cd infra && terraform init -reconfigure -input=false -backend-config=env/$(ENV).backend.hcl
	cd infra && terraform apply $(ENV).tfplan
	rm infra/$(ENV).tfplan
	
all: style unit_test integration_test

