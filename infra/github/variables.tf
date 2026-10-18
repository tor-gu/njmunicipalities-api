variable "region" {
  type    = string
  default = "us-east-1"
}

variable "project" {
  description = "Prefix for the role names, and the state key prefix in state_bucket"
  type        = string
}

variable "github_repo" {
  description = "owner/name of the GitHub repository whose workflows may assume the roles"
  type        = string
}

variable "envs" {
  description = "Deploy environments, keyed by GitHub environment name (prod deploys from main, dev from dev)"
  type = map(object({
    env_prefix = string # matches env_prefix in ../env/<env>.tfvars and EnvPrefix in template.yaml
    stack_name = string # the SAM stack
  }))
}

variable "state_bucket" {
  description = "Bucket holding the Terraform state of ../ (keys <project>/<env>.tfstate)"
  type        = string
}

variable "cfn_execution_role_arn" {
  description = "Role CloudFormation assumes for sam deploy (shared with other SAM projects)"
  type        = string
}

variable "sam_artifact_bucket" {
  description = "Bucket sam deploy uploads packaged code to (shared with other SAM projects)"
  type        = string
}

variable "torguapi_layer_name" {
  description = "Name of the torguapi Lambda layer, which the unit tests download"
  type        = string
}
