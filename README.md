
# njmunicipalities-api

This is the source code for the NJ Municipalities API deployed at
`api.tor-gu.com`.

It contains the names and GEOID/FIPS codes for every municipality and
county in NJ, from 2000 to 2022, and records the changes from year to
year.

See the related [njmunicipalities data pacakge for
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
municipalities for 2022 into a [pandas
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


# Load municipality tables for 2022
municipalities_2022 = load_as_df("https://api.tor-gu.com/nj/municipalities/2022")
```

| year | GEOID      | county          | municipality         |
| ---: | :--------- | :-------------- | :------------------- |
| 2022 | 3400100100 | Atlantic County | Absecon city         |
| 2022 | 3400102080 | Atlantic County | Atlantic City city   |
| 2022 | 3400107810 | Atlantic County | Brigantine city      |
| 2022 | 3400108680 | Atlantic County | Buena borough        |
| 2022 | 3400108710 | Atlantic County | Buena Vista township |
| 2022 | 3400115160 | Atlantic County | Corbin City city     |

The `municipality_xrefs` endpoint works similarly. As an example, let’s
also retrieve the 2000 municipality table along with the 2022/2000
cross-reference table, and take a look at the changes in NJ
municipalties between 2000 and 2022.

``` python
municipalities_2000 = load_as_df("https://api.tor-gu.com/nj/municipalities/2000")
xrefs = load_as_df("https://api.tor-gu.com/nj/municipality_xrefs/2022/2000")
# Select columns for a merged table
xrefs = xrefs.rename(
    columns={"GEOID_ref": "GEOID_2022", "GEOID": "GEOID_2000"}
    )[["GEOID_2000", "GEOID_2022"]]
municipalities_2000 = municipalities_2000.rename(
    columns={"GEOID": "GEOID_2000", "municipality": "municipality_2000"}
    )[["GEOID_2000", "county", "municipality_2000"]]
municipalities_2022 = municipalities_2022.rename(
    columns={"GEOID": "GEOID_2022", "municipality": "municipality_2022"}
    )[["GEOID_2022","municipality_2022"]]

# Create the merged table
merged = xrefs.merge(
    municipalities_2000, how="left", on="GEOID_2000").merge(
    municipalities_2022, how="left", on="GEOID_2022").fillna("NA")

# Select all changes in municipalities between 2000 and 20222
changes = merged[(merged["municipality_2000"] != merged["municipality_2022"]) | 
    (merged["GEOID_2000"] != merged["GEOID_2022"])]
```

|     | GEOID\_2000 | GEOID\_2022 | county          | municipality\_2000    | municipality\_2022    |
| :-- | :---------- | :---------- | :-------------- | :-------------------- | :-------------------- |
| 161 | 3400758920  | NA          | Camden County   | Pine Valley borough   | NA                    |
| 202 | 3401309220  | 3401309250  | Essex County    | Caldwell borough      | Caldwell borough      |
| 292 | 3402160900  | 3402160900  | Mercer County   | Princeton borough     | Princeton             |
| 293 | 3402160915  | NA          | Mercer County   | Princeton township    | NA                    |
| 295 | 3402177210  | 3402163850  | Mercer County   | Washington township   | Robbinsville township |
| 367 | 3402568670  | 3402537560  | Monmouth County | South Belmar borough  | Lake Como borough     |
| 421 | 3402918130  | 3402973125  | Ocean County    | Dover township        | Toms River township   |
| 462 | 3403179820  | 3403182423  | Passaic County  | West Paterson borough | Woodland Park borough |

## Deploying

This API is implemented as an [AWS
SAM](https://aws.amazon.com/serverless/sam/) application. It depends on
a lambda layer
[layer\_torguapi](https://github.com/tor-gu/layer_torguapi), which needs
to be deployed separately. You also need to have CSV dumps of the tables
in [njmunicipalities](https://github.com/tor-gu/njmunicipalities)
available in an S3 bucket.

### Direct deploy

The application can be deployed directly using the SAM CLI:

    sam build
    sam deploy --stack-name MyStackName
               --template template.yaml
               --parameter-overrides                                                            \
                    TorguapiLayerArn=arn:aws:lambda:us-east-1:123456789012:layer:layer_torguapi \
                    TorguapiLayerVersion=1                                                      \
                    ApiRoot=https://api.example.com 

Replace the `TorguapiLayerXXX` params with the values derived from the
`layer_torguapi` deployment.

The `ApiRoot` value is used only for generating the values in `"links"`
in the JSON reply. On `api.tor-gu.com`, the relationship between the
publicly facing API URL and the API Gateway endpoints is configured in
[torgu-api-cloudfront](https://github.com/tor-gu/torgu-api-cloudfront).

### Using a pipeline

The package also include the code pipeline that I use to deploy from
github.

In addition to the requirements above, you will need to have execution
roles for the pipeline (`PipelineExecutionRole`) and for the deployment
itself (`CloudFormationExecutionRole`).

    aws cloudformation deploy --stack-name MyPiplineStackName \
        --template-body file://codepipeline.yaml                    \
        --capabilities CAPABILITY_IAM                               \
        --parameters \
            ParameterKey=ArtifactBucket,ParameterValue=MyArtifactBucket \
            ParameterKey=PipelineExecutionRole,ParameterValue=arn:aws:iam::123456789012:role/MyPipelineExecutionRole \
            ParameterKey=CloudFormationExecutionRole,ParameterValue=arn:aws:iam::123456789012:role/MyCloudFormationExecutionRole \
            ParameterKey=Region,ParameterValue=us-east-1 \
            ParameterKey=DeployStackName,ParameterValue=MyStackName \
            ParameterKey=TorguapiLayerArn,ParameterValue=arn:aws:lambda:us-east-1:123456789012:layer:layer_torguapi \
            ParameterKey=TorguapiLayerVersion,ParameterValue=1 \
            ParameterKey=ApiRoot,ParameterValue=https://api.example.com
