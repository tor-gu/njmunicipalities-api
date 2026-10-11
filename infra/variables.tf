variable "region" {
  type    = string
  default = "us-east-1"
}

variable "env_prefix" {
  description = "Prefix for resource names (matches EnvPrefix in template.yaml)"
  type        = string
}
