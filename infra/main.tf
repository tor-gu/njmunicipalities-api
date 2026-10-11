# DynamoDB tables read by the njmunicipalities-api lambdas.
#
# The lambdas defined in template.yaml find these tables by name, so the names
# here must match TABLE_COUNTIES and TABLE_MUNICIPALITIES there. Terraform
# manages the tables only, not their contents.

locals {
  counties_table_name       = "${var.env_prefix}counties"
  municipalities_table_name = "${var.env_prefix}municipalities"
}

resource "aws_dynamodb_table" "counties" {
  name                        = local.counties_table_name
  billing_mode                = "PAY_PER_REQUEST"
  hash_key                    = "row_number"
  deletion_protection_enabled = true

  attribute {
    name = "row_number"
    type = "N"
  }

  point_in_time_recovery {
    enabled = true
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_dynamodb_table" "municipalities" {
  name                        = local.municipalities_table_name
  billing_mode                = "PAY_PER_REQUEST"
  hash_key                    = "row_number"
  deletion_protection_enabled = true

  attribute {
    name = "row_number"
    type = "N"
  }

  point_in_time_recovery {
    enabled = true
  }

  lifecycle {
    prevent_destroy = true
  }
}
