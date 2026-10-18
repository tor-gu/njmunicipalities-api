# IAM roles assumed by this repo's GitHub Actions workflow
# (.github/workflows/deploy.yml) through OIDC.
#
# The OIDC provider is account-wide and lives in the shared aws-infra repo.
# Each role trusts only tokens whose sub claim names this repo and either a
# branch (readonly) or a GitHub environment (deploy). The prod environment
# requires approval, so the prod deploy role is unusable until a run on main
# is approved.
#
# Copy this module for another project by changing terraform.tfvars and the
# project-specific statements (tables, loader) below.

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

data "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"
}

locals {
  account = data.aws_caller_identity.current.account_id
  region  = data.aws_region.current.region

  oidc_host = "token.actions.githubusercontent.com"

  table_arns = {
    for env, cfg in var.envs : env => [
      for table in ["counties", "municipalities"] :
      "arn:aws:dynamodb:${local.region}:${local.account}:table/${cfg.env_prefix}${table}"
    ]
  }

  stack_arns = {
    for env, cfg in var.envs : env =>
    "arn:aws:cloudformation:${local.region}:${local.account}:stack/${cfg.stack_name}/*"
  }

  # The state of ../, one key per environment
  state_key_arns = {
    for env in keys(var.envs) : env =>
    "arn:aws:s3:::${var.state_bucket}/${var.project}/${env}.tfstate"
  }

  layer_arn = "arn:aws:lambda:${local.region}:${local.account}:layer:${var.torguapi_layer_name}:*"

  # Terraform's reads of aws_dynamodb_table (plan and refresh)
  dynamodb_read_actions = [
    "dynamodb:DescribeTable",
    "dynamodb:DescribeContinuousBackups",
    "dynamodb:DescribeTimeToLive",
    "dynamodb:ListTagsOfResource",
    "dynamodb:GetResourcePolicy",
  ]
}

# --- readonly ---
# Unit tests, terraform plan, loader dry run, integration test. Any job on dev
# or main may use it, so it must not be able to change anything.

data "aws_iam_policy_document" "readonly_trust" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [data.aws_iam_openid_connect_provider.github.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "${local.oidc_host}:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "${local.oidc_host}:sub"
      values = [
        "repo:${var.github_repo}:ref:refs/heads/dev",
        "repo:${var.github_repo}:ref:refs/heads/main",
      ]
    }
  }
}

data "aws_iam_policy_document" "readonly" {
  statement {
    sid       = "FetchTorguapiLayer"
    actions   = ["lambda:GetLayerVersion"]
    resources = [local.layer_arn]
  }

  statement {
    sid       = "PlanAndDryRun"
    actions   = concat(local.dynamodb_read_actions, ["dynamodb:Scan"])
    resources = flatten(values(local.table_arns))
  }

  # terraform plan -lock=false: reads state, never writes the lock file
  statement {
    sid       = "ReadState"
    actions   = ["s3:GetObject"]
    resources = values(local.state_key_arns)
  }

  statement {
    sid       = "ListState"
    actions   = ["s3:ListBucket"]
    resources = ["arn:aws:s3:::${var.state_bucket}"]

    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values   = ["${var.project}/*"]
    }
  }

  # tests/integration finds the API URLs in the dev stack's outputs
  statement {
    sid       = "IntegrationTest"
    actions   = ["cloudformation:DescribeStacks"]
    resources = [local.stack_arns["dev"]]
  }
}

resource "aws_iam_role" "readonly" {
  name               = "${var.project}-gha-readonly"
  assume_role_policy = data.aws_iam_policy_document.readonly_trust.json
}

resource "aws_iam_role_policy" "readonly" {
  name   = "readonly"
  role   = aws_iam_role.readonly.id
  policy = data.aws_iam_policy_document.readonly.json
}

# --- deploy ---
# One role per environment: terraform apply, data load, sam deploy.

data "aws_iam_policy_document" "deploy_trust" {
  for_each = var.envs

  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [data.aws_iam_openid_connect_provider.github.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "${local.oidc_host}:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "${local.oidc_host}:sub"
      values   = ["repo:${var.github_repo}:environment:${each.key}"]
    }
  }
}

data "aws_iam_policy_document" "deploy" {
  for_each = var.envs

  # Terraform for the tables in ../
  statement {
    sid = "TerraformTables"
    actions = concat(local.dynamodb_read_actions, [
      "dynamodb:UpdateTable",
      "dynamodb:UpdateContinuousBackups",
      "dynamodb:UpdateTimeToLive",
      "dynamodb:TagResource",
      "dynamodb:UntagResource",
    ])
    resources = local.table_arns[each.key]
  }

  statement {
    sid = "TerraformState"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
    ]
    resources = [
      local.state_key_arns[each.key],
      "${local.state_key_arns[each.key]}.tflock",
    ]
  }

  statement {
    sid       = "TerraformListState"
    actions   = ["s3:ListBucket"]
    resources = ["arn:aws:s3:::${var.state_bucket}"]

    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values   = ["${var.project}/*"]
    }
  }

  # scripts/load_data.py
  statement {
    sid = "LoadData"
    actions = [
      "dynamodb:Scan",
      "dynamodb:BatchWriteItem",
    ]
    resources = local.table_arns[each.key]
  }

  # sam deploy: CloudFormation does the work as cfn_execution_role_arn; this
  # role only uploads the code and drives the change set. Adapted from the
  # SAM-managed PipelineExecutionRole.
  statement {
    sid       = "SamPassRole"
    actions   = ["iam:PassRole"]
    resources = [var.cfn_execution_role_arn]

    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"
      values   = ["cloudformation.amazonaws.com"]
    }
  }

  statement {
    sid = "SamStack"
    actions = [
      "cloudformation:CreateChangeSet",
      "cloudformation:DescribeChangeSet",
      "cloudformation:ExecuteChangeSet",
      "cloudformation:DeleteChangeSet",
      "cloudformation:DescribeStacks",
      "cloudformation:DescribeStackEvents",
      "cloudformation:DescribeStackResource",
      "cloudformation:GetTemplate",
    ]
    resources = [local.stack_arns[each.key]]
  }

  # template.yaml uses the Serverless and AWS::Include transforms
  statement {
    sid     = "SamTransforms"
    actions = ["cloudformation:CreateChangeSet"]
    resources = [
      "arn:aws:cloudformation:${local.region}:aws:transform/Serverless-2016-10-31",
      "arn:aws:cloudformation:${local.region}:aws:transform/Include",
    ]
  }

  statement {
    sid = "SamTemplate"
    actions = [
      "cloudformation:GetTemplateSummary",
      "cloudformation:ValidateTemplate",
    ]
    resources = ["*"]
  }

  # The artifact bucket is shared, so only this stack's prefix
  statement {
    sid = "SamArtifacts"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
    ]
    resources = ["arn:aws:s3:::${var.sam_artifact_bucket}/${each.value.stack_name}/*"]
  }

  statement {
    sid = "SamArtifactsBucket"
    actions = [
      "s3:GetBucketLocation",
      "s3:ListBucket",
    ]
    resources = ["arn:aws:s3:::${var.sam_artifact_bucket}"]
  }

  statement {
    sid       = "FetchTorguapiLayer"
    actions   = ["lambda:GetLayerVersion"]
    resources = [local.layer_arn]
  }
}

resource "aws_iam_role" "deploy" {
  for_each = var.envs

  name               = "${var.project}-gha-deploy-${each.key}"
  assume_role_policy = data.aws_iam_policy_document.deploy_trust[each.key].json
}

resource "aws_iam_role_policy" "deploy" {
  for_each = var.envs

  name   = "deploy"
  role   = aws_iam_role.deploy[each.key].id
  policy = data.aws_iam_policy_document.deploy[each.key].json
}
