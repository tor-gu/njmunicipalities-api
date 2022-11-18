export PYTHONPATH = common_layer
export AWS_SAM_STACK_NAME=NjMunicipalitiesApiDev

src_dirs := common_layer counties municipalities tests

style:
	python -m isort $(src_dirs)
	python -m black --target-version py39 $(src_dirs)
	python -m flake8 --ignore E501,E203,W503 --exclude .aws-sam,torguapi

unit_test:
	python -m pytest -sv tests/unit

integration_test:
	python -m pytest -sv tests/integration

knit:
	Rscript -e "rmarkdown::render('README.Rmd')"
	
all: style unit_test integration_test

