output "counties_table_name" {
  value = aws_dynamodb_table.counties.name
}

output "municipalities_table_name" {
  value = aws_dynamodb_table.municipalities.name
}
