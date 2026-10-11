# The tables predate Terraform: they were created by SAM, now
# owned by TF.

import {
  to = aws_dynamodb_table.counties
  id = local.counties_table_name
}

import {
  to = aws_dynamodb_table.municipalities
  id = local.municipalities_table_name
}
