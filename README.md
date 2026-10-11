
# njmunicipalities-api

This is the source code for the NJ Municipalities API deployed at
`api.tor-gu.com`.

It contains the names and GEOID/FIPS codes for every municipality and
county in NJ, from 2000 to 2025, and records the changes from year to
year.

See the related [njmunicipalities data package for
R](https://github.com/tor-gu/njmunicipalities) for more details on the
underlying dataset.

## Try it out

### OpenAPI/Swagger

There is an OpenAPI/swagger document deployed
[here](https://tor-gu.com/apis/njmunicipalities.html) that you can play
with.

### Sample code

Each endpoint returns paginated results, with a `"next"` url in the
`"links"` section indicating that there are more results to be
retrieved.

This is illustrated in the python code below, which loads the table of
municipalities for 2025 into a [pandas
DataFrame](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.html).

``` python
import json
import requests
import pandas as pd


def load_as_df(url):
    """Retrieve entire dataset at url and return as a dataframe"""
    # Get the first page
    resp = requests.get(url)
    resp.raise_for_status()
    resp_json = json.loads(resp.content.decode('utf-8'))
    df = pd.DataFrame(resp_json["data"])
    
    # Keep retrieving pages while there is a 'next' link
    while "next" in resp_json["links"]:
        resp = requests.get(resp_json["links"]["next"])
        resp.raise_for_status()
        resp_json = json.loads(resp.content.decode('utf-8'))
        df = pd.concat([df, pd.DataFrame(resp_json["data"])], ignore_index = True)
    return df


# Load municipality tables for 2025
municipalities_2025 = load_as_df("https://api.tor-gu.com/nj/municipalities/2025")
```

| year | GEOID      | county          | municipality         |
|-----:|:-----------|:----------------|:---------------------|
| 2025 | 3400100100 | Atlantic County | Absecon city         |
| 2025 | 3400102080 | Atlantic County | Atlantic City city   |
| 2025 | 3400107810 | Atlantic County | Brigantine city      |
| 2025 | 3400108680 | Atlantic County | Buena borough        |
| 2025 | 3400108710 | Atlantic County | Buena Vista township |
| 2025 | 3400115160 | Atlantic County | Corbin City city     |

The `municipality_xrefs` endpoint works similarly. As an example, let’s
also retrieve the 2000 municipality table along with the 2025/2000
cross-reference table, and take a look at the changes in NJ
municipalities between 2000 and 2025.

``` python
municipalities_2000 = load_as_df("https://api.tor-gu.com/nj/municipalities/2000")
xrefs = load_as_df("https://api.tor-gu.com/nj/municipality_xrefs/2025/2000")
# Select columns for a merged table
xrefs = xrefs.rename(
    columns={"GEOID_ref": "GEOID_2025", "GEOID": "GEOID_2000"}
    )[["GEOID_2000", "GEOID_2025"]]
municipalities_2000 = municipalities_2000.rename(
    columns={"GEOID": "GEOID_2000", "municipality": "municipality_2000"}
    )[["GEOID_2000", "county", "municipality_2000"]]
municipalities_2025 = municipalities_2025.rename(
    columns={"GEOID": "GEOID_2025", "municipality": "municipality_2025"}
    )[["GEOID_2025","municipality_2025"]]

# Create the merged table
merged = xrefs.merge(
    municipalities_2000, how="left", on="GEOID_2000").merge(
    municipalities_2025, how="left", on="GEOID_2025").fillna("NA")

# Select all changes in municipalities between 2000 and 2025
changes = merged[(merged["municipality_2000"] != merged["municipality_2025"]) | 
    (merged["GEOID_2000"] != merged["GEOID_2025"])]
```

|     | GEOID_2000 | GEOID_2025 | county          | municipality_2000     | municipality_2025     |
|:----|:-----------|:-----------|:----------------|:----------------------|:----------------------|
| 161 | 3400758920 | NA         | Camden County   | Pine Valley borough   | NA                    |
| 202 | 3401309220 | 3401309250 | Essex County    | Caldwell borough      | Caldwell borough      |
| 292 | 3402160900 | 3402160900 | Mercer County   | Princeton borough     | Princeton             |
| 293 | 3402160915 | NA         | Mercer County   | Princeton township    | NA                    |
| 295 | 3402177210 | 3402163850 | Mercer County   | Washington township   | Robbinsville township |
| 367 | 3402568670 | 3402537560 | Monmouth County | South Belmar borough  | Lake Como borough     |
| 421 | 3402918130 | 3402973125 | Ocean County    | Dover township        | Toms River township   |
| 462 | 3403179820 | 3403182423 | Passaic County  | West Paterson borough | Woodland Park borough |

## Deploying

This API is implemented as an [AWS
SAM](https://aws.amazon.com/serverless/sam/) application, with its
DynamoDB tables managed separately by
[Terraform](https://www.terraform.io/). A deployment has four parts:

1.  The lambda layer
    [layer_torguapi](https://github.com/tor-gu/layer_torguapi), which
    needs to be deployed separately.
2.  The DynamoDB tables, defined in `infra/`.
3.  The data: CSV exports of the tables in
    [njmunicipalities](https://github.com/tor-gu/njmunicipalities),
    committed in `data/` and loaded into the tables by
    `scripts/load_data.py`.
4.  The lambdas and API Gateway, defined in `template.yaml`.

The tables are kept out of the SAM template. Terraform owns the
tables, and the loader owns their contents.

### Tables

Terraform state is kept in an S3 bucket, with one state file per
environment (see `infra/env/*.backend.hcl`; the bucket must exist and
should be versioned).

    make tf_plan ENV=dev      # review the plan, then
    make tf_apply ENV=dev

### Data

`data/` holds `counties.csv`, `municipalities.csv`, and `SOURCE`, which
records the njmunicipalities release they were exported from. To export
a release (this needs R and the `remotes` package; the release is
installed into a temporary library):

    make export_data REF=v1.4.0

`scripts/load_data.py` brings the tables in line with `data/`: rows that
are new or changed are written, and rows no longer in the CSVs are
deleted. To preview what it would change:

    make load_dry_run ENV=dev

The pipeline runs the loader on every deploy.

### Data update workflow

1.  `make export_data REF=<new release>`.
2.  Update the hard-coded current year, if necessary: `DEFAULT_YEAR` in
    `municipalities/app/municipalities_lib.py`, the examples in
    `njmunicipalities-openapi.yaml` and in this README (then
    `make knit`), and the unit tests.
3.  `make load_dry_run ENV=dev` to preview the load.
4.  Push to `dev`, check the dev API, then merge to `master`.

### Direct deploy

The application can be deployed directly using the SAM CLI. Load the
data first, then deploy with the matching `DataVersion`:

    python scripts/load_data.py
    sam build
    sam deploy --stack-name MyStackName                                                         \
               --capabilities CAPABILITY_IAM                                                    \
               --resolve-s3                                                                     \
               --parameter-overrides                                                            \
                    TorguapiLayerArn=arn:aws:lambda:us-east-1:123456789012:layer:layer_torguapi \
                    TorguapiLayerVersion=1                                                      \
                    ApiRoot=https://api.example.com                                             \
                    DataVersion=$(sed -n 's/^version=//p' data/SOURCE)

Replace the `TorguapiLayerXXX` params with the values derived from the
`layer_torguapi` deployment.

The `ApiRoot` value is used only for generating the values in `"links"`
in the JSON reply. On `api.tor-gu.com`, the relationship between the
publicly facing API URL and the API Gateway endpoints is configured in
[torgu-api-cloudfront](https://github.com/tor-gu/torgu-api-cloudfront).

To deploy a second environment alongside the first, give it a resource
name prefix (I use `dev-`): set `EnvPrefix` in the template parameters,
`--env-prefix` for the loader, and `env_prefix` in `infra/env/*.tfvars`.

### Using a pipeline

The package also includes the code pipeline that I use to deploy from
github. Each run updates the pipeline itself, runs the unit tests,
builds the application, loads the data, and deploys.

In addition to the requirements above, you will need to have execution
roles for the pipeline (`PipelineExecutionRole`) and for the deployment
itself (`CloudFormationExecutionRole`). The pipeline’s CodeBuild role is
granted read and batch-write access to the environment’s two tables, for
the data load.

    aws cloudformation deploy --stack-name MyPipelineStackName \
        --template-file codepipeline.yaml \
        --capabilities CAPABILITY_IAM \
        --parameter-overrides \
            ArtifactBucket=MyArtifactBucket \
            PipelineExecutionRole=arn:aws:iam::123456789012:role/MyPipelineExecutionRole \
            CloudFormationExecutionRole=arn:aws:iam::123456789012:role/MyCloudFormationExecutionRole \
            Region=us-east-1 \
            DeployStackName=MyStackName \
            TorguapiLayerArn=arn:aws:lambda:us-east-1:123456789012:layer:layer_torguapi \
            TorguapiLayerVersion=1 \
            ApiRoot=https://api.example.com
