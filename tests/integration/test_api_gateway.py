import os
from unittest import TestCase

import boto3
import requests

"""
Make sure env variable AWS_SAM_STACK_NAME exists with the name of the stack we are going to test.
"""


class TestApiGateway(TestCase):
    api_endpoint: str

    @classmethod
    def get_and_verify_stack_name(cls) -> str:
        stack_name = os.environ.get("AWS_SAM_STACK_NAME")
        if not stack_name:
            raise Exception(
                "Cannot find env var AWS_SAM_STACK_NAME. \n"
                "Please setup this environment variable with the stack name where we are running integration tests."
            )

        # Verify stack exists
        client = boto3.client("cloudformation")
        try:
            client.describe_stacks(StackName=stack_name)
        except Exception as e:
            raise Exception(
                f"Cannot find stack {stack_name}. \n"
                f'Please make sure stack with the name "{stack_name}" exists.'
            ) from e

        return stack_name

    def setUp(self) -> None:
        """
        Based on the provided env variable AWS_SAM_STACK_NAME,
        here we use cloudformation API to find out what the CountiesApi and MunicipalitiesApi URLs are
        """
        stack_name = TestApiGateway.get_and_verify_stack_name()

        client = boto3.client("cloudformation")

        response = client.describe_stacks(StackName=stack_name)
        stacks = response["Stacks"]
        self.assertTrue(stacks, f"Cannot find stack {stack_name}")

        stack_outputs = stacks[0]["Outputs"]
        counties_api_outputs = [
            output
            for output in stack_outputs
            if output["OutputKey"] == "CountiesFunctionApiGateway"
        ]
        self.assertTrue(
            counties_api_outputs,
            f"Cannot find output CountiesFunctionApiGateway in stack {stack_name}",
        )
        municipalities_api_outputs = [
            output
            for output in stack_outputs
            if output["OutputKey"] == "MunicipalitiesFunctionApiGateway"
        ]
        self.assertTrue(
            municipalities_api_outputs,
            f"Cannot find output MunicipalitiesFunctionApiGateway in stack {stack_name}",
        )
        xrefs_api_outputs = [
            output
            for output in stack_outputs
            if output["OutputKey"] == "XREFsFunctionApiGateway"
        ]
        self.assertTrue(
            xrefs_api_outputs,
            f"Cannot find output XREFsFunctionApiGateway in stack {stack_name}",
        )

        self.counties_api_endpoint = counties_api_outputs[0]["OutputValue"]
        self.municipalities_api_endpoint = municipalities_api_outputs[0]["OutputValue"]
        self.xrefs_api_endpoint = xrefs_api_outputs[0]["OutputValue"]

    def test_counties_api_gateway(self):
        """
        Make request to the Counties REST API, verify the response has the
        proper keys.
        """
        response = requests.get(self.counties_api_endpoint)
        self.assertEqual(response.status_code, 200)
        county = response.json()["data"][1]
        self.assertIn("GEOID", county)
        self.assertIn("county", county)

    def test_municipalities_api_gateway(self):
        """
        Make request to the Municipalities REST API, verify the response has the
        proper keys.
        """
        response = requests.get(self.municipalities_api_endpoint)
        self.assertEqual(response.status_code, 200)
        municipality = response.json()["data"][1]
        self.assertIn("year", municipality)
        self.assertIn("GEOID", municipality)
        self.assertIn("county", municipality)
        self.assertIn("municipality", municipality)

    def test_xrefs_api_gateway(self):
        """
        Make request to the XREFs REST API, verify the response has the
        proper keys.
        """
        xref_url = f"{self.xrefs_api_endpoint}2000/2001"
        response = requests.get(xref_url)
        self.assertEqual(response.status_code, 200)
        xref = response.json()["data"][1]
        self.assertIn("GEOID_ref", xref)
        self.assertIn("GEOID", xref)
        self.assertIn("year", xref)
        self.assertIn("year_ref", xref)
