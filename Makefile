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
	
all: style unit_test integration_test

