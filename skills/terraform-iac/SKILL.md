---
name: terraform-iac
description: Use this skill when a Jira ticket's intent is about generating, validating, or fixing Terraform Infrastructure as Code (IaC) for AWS resources. This covers writing HCL configuration files, running terraform init, plan, and validate, and fixing syntax or structural errors. Do not use for unrelated requests (e.g. application code, non-Terraform topics, Salesforce/Dynamics migration).
---

# terraform-iac

## Overview

This skill covers generating and validating Terraform HCL configurations for
AWS infrastructure. It applies whenever a ticket's intent involves creating
or fixing Terraform code for AWS resources.

All files (main.tf, plan.md, results.md) are written to the workspace path
passed by the orchestrator via the `write_file` tool. This workspace is a
virtual filesystem backed by agent state — do NOT use absolute system paths
like `/workspace/` or `~/`. Always use the exact workspace path string the
orchestrator provided.

The three subagents use this skill as follows:
- **Planner** — sections 1, 2, 3 (parse requirements, design HCL structure, build plan.md)
- **Executor** — section 3 (write main.tf, run terraform init/plan/validate, write results.md)
- **Validator** — section 5 (validation checklist comparing plan.md against results.md)
- **All** — section 6 (error handling) and section 7 (retry awareness)

---

## Instructions

### 1. Pre-flight: identify AWS resources in scope

Before building any plan, explicitly list every AWS resource found in the
ticket and note where each was mentioned (summary / description / comment).

Write this list at the top of plan.md under a `## Resources in scope` heading.

If no resources are mentioned anywhere in the ticket, do **not** assume a
default set. Instead, call `post_jira_comment` asking the reporter to specify
which AWS resources need to be provisioned, and stop. Do not proceed to
planning until the ticket is clarified.

---

### 2. Design the HCL structure

For each AWS resource in scope, determine:
- The correct Terraform resource type (e.g. `aws_instance`, `aws_s3_bucket`, `aws_vpc`)
- Required arguments vs optional arguments
- Dependencies between resources (e.g. a subnet depends on a VPC)
- Correct resource ordering in main.tf (dependencies first)
- ALWAYS GIVE SINGLE FINAL FILE OF CODE. NO MULTI-FILE CODE.

Use this dependency reference when sequencing:

| Resource                          | Depends on (must be defined first)         |
|-----------------------------------|--------------------------------------------|
| aws_subnet                        | aws_vpc                                    |
| aws_internet_gateway              | aws_vpc                                    |
| aws_route_table                   | aws_vpc                                    |
| aws_route_table_association       | aws_subnet, aws_route_table                |
| aws_security_group                | aws_vpc                                    |
| aws_instance                      | aws_subnet, aws_security_group             |
| aws_db_instance                   | aws_subnet (via aws_db_subnet_group)       |
| aws_db_subnet_group               | aws_subnet                                 |
| aws_lb                            | aws_subnet, aws_security_group             |
| aws_lb_target_group               | aws_vpc                                    |
| aws_lb_listener                   | aws_lb, aws_lb_target_group                |
| aws_ecs_service                   | aws_ecs_cluster, aws_lb_target_group       |
| aws_ecs_task_definition           | (none)                                     |
| aws_ecs_cluster                   | (none)                                     |
| aws_iam_role_policy_attachment    | aws_iam_role, aws_iam_policy               |

Rules:
- Never define a resource before all of its dependencies in main.tf.
- Resources with no dependencies go first, in any order among themselves.
- If a resource is not in this table, treat it as having no known
  dependencies but flag it in plan.md as:

  `⚠ DEPENDENCY UNKNOWN — verify before provisioning: <ResourceType>`

---

### 3. Build plan.md and write main.tf

**plan.md must include:**
Resources in scope
<resource_type>.<name>: <description>
HCL structure

<N>. Define <resource_type>.<name>

Required args: <list>
Depends on: <list> | none
Dependency flag: <⚠ DEPENDENCY UNKNOWN> | (omit if known)
Validation steps
Run: terraform init -backend=false -get=false -input=false -no-color
Run: terraform validate -json
Parse validate JSON output — passed only if init exits 0 and "valid": true

**Executor steps (in order):**

1. Write the complete HCL to `{workspace_path}/main.tf` using `write_file`.
   The workspace path is the exact string the orchestrator passed — do not
   modify or abbreviate it. The file must include:
   - A `terraform` block with `required_providers` specifying the AWS provider
   - A `provider "aws"` block with `region` set (default to `us-east-1` if not specified)
   - All resource blocks in dependency order

2. Call `validate_terraform_configuration` with the complete HCL in main.tf.
   This tool runs `terraform init -backend=false -get=false -input=false
   -no-color`, then `terraform validate -json`, in an isolated temporary
   directory. It accepts only the official AWS provider and does not fetch
   Terraform modules. AWS credentials are not required.
   - If init fails, read the error and fix main.tf before retrying.
   - If validation returns `"valid": false`, read `diagnostics`, fix the
     specific errors, and call the tool again.
   - The tool never runs `terraform plan`, `apply`, or `destroy`. Do not
     claim that infrastructure was deployed.

3. Write results.md to `{workspace_path}/results.md` with:
   - Reference to main.tf by path (do NOT copy its full content into results.md)
   - The complete validation tool report
   - Pass/fail validation status
   - Any unresolved errors under `## Unresolved errors`

---

### 4. Known AWS resource reference

| AWS Resource              | Terraform Type                    | Key Required Args                                        |
|---------------------------|-----------------------------------|----------------------------------------------------------|
| VPC                       | aws_vpc                           | cidr_block                                               |
| Subnet                    | aws_subnet                        | vpc_id, cidr_block, availability_zone                    |
| Internet Gateway          | aws_internet_gateway              | vpc_id                                                   |
| Security Group            | aws_security_group                | vpc_id, ingress, egress                                  |
| EC2 Instance              | aws_instance                      | ami, instance_type, subnet_id                            |
| S3 Bucket                 | aws_s3_bucket                     | bucket                                                   |
| RDS Instance              | aws_db_instance                   | identifier, engine, instance_class, db_subnet_group_name |
| ECS Cluster               | aws_ecs_cluster                   | name                                                     |
| ECS Task Definition       | aws_ecs_task_definition           | family, container_definitions                            |
| IAM Role                  | aws_iam_role                      | name, assume_role_policy                                 |
| Lambda Function           | aws_lambda_function               | function_name, role, handler, runtime                    |
| API Gateway               | aws_api_gateway_rest_api          | name                                                     |

Any resource **not** in this table has no confirmed mapping. Flag it in
plan.md as:

`⚠ NO TERRAFORM MAPPING — manual review required: <ResourceName>`

---

### 5. Validation checklist (for the validator subagent)

Read plan.md and results.md from the workspace path. Call
`submit_validation_verdict` with `passed=True` only if **all** items below
pass. For any failure, list the specific failed item in the `gaps` field.
Do NOT check for exec_summary.md — that is written by the orchestrator after
validation completes and does not exist at the time the validator runs.

**Scope**
- [ ] All resources listed in plan.md `## Resources in scope` appear in main.tf.
      No resources were silently skipped.

**HCL correctness**
- [ ] `terraform validate -json` output in results.md shows `"valid": true`.
- [ ] No `diagnostics` entries with `"severity": "error"` in the validate output.
- [ ] The `required_providers` block is present with the AWS provider specified.
- [ ] The `provider "aws"` block is present with a region.

**Dependency order**
- [ ] No resource is defined before all of its dependencies in main.tf.
      Cross-check the resource order in main.tf against the dependency table
      in section 2.

**Results documentation**
- [ ] results.md contains the full validation tool report.
- [ ] results.md clearly states whether validation passed or failed.
- [ ] main.tf exists at the workspace path and is non-empty.

---

### 6. Error handling

If `terraform validate -json` returns `"valid": false`:

1. Read the `diagnostics` array carefully. Each entry has:
   - `"severity"`: `"error"` or `"warning"`
   - `"summary"`: short description of the problem
   - `"detail"`: longer explanation
   - `"range"`: file and line number of the error

2. Fix **only the specific lines** flagged in `range`. Do not rewrite the
   entire file unless the structure is fundamentally wrong.

3. Re-run `validate_terraform_configuration` after each fix.

4. If the same error persists after 2 fix attempts, write it to results.md
   under `## Unresolved errors` and surface it to the validator rather than
   looping infinitely.

5. Warnings (not errors) do not block a `passed=True` verdict — note them
   in results.md but do not treat them as failures.

---

### 7. Retry awareness

If the orchestrator retries the executor after a failed validation:

1. Read results.md before starting. Check `## Unresolved errors` — do not
   re-attempt fixes that already failed twice.
2. Read the validator's feedback.md for the specific gaps identified.
3. Address only the gaps listed in feedback.md. Do not rewrite resources
   that were already validated successfully.
4. Note at the top of the retry results.md section:
   `## Retry run — addressing gaps: <list from feedback.md>`