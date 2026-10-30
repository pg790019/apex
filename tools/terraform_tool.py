"""Restricted Terraform validation tool for generated AWS IaC."""

import json
import re
import subprocess
import tempfile
from pathlib import Path

from langchain_core.tools import tool

from logging_setup import get_logger

logger = get_logger(__name__)

_COMMAND_TIMEOUT_SECONDS = 180
_PROVIDER_SOURCE_PATTERN = re.compile(
    r'(?m)^\s*source\s*=\s*"([^"]+)"'
)
_MODULE_BLOCK_PATTERN = re.compile(r'(?m)^\s*module\s+"')


@tool
def validate_terraform_configuration(main_tf: str) -> str:
    """Run Terraform init and validate on a single AWS-provider main.tf file.

    The tool uses a temporary directory, disables backend and module
    initialization, and never runs plan, apply, or destroy. AWS credentials
    are not required for these checks.

    Args:
        main_tf: Complete Terraform configuration to validate.

    Returns:
        JSON report with init/validate status and command output.
    """
    provider_sources = _PROVIDER_SOURCE_PATTERN.findall(main_tf)
    if "hashicorp/aws" not in provider_sources:
        return json.dumps({
            "passed": False,
            "stage": "preflight",
            "error": 'Configuration must declare the official "hashicorp/aws" provider.',
        })
    if any(source != "hashicorp/aws" for source in provider_sources):
        return json.dumps({
            "passed": False,
            "stage": "preflight",
            "error": "Only the official hashicorp/aws provider is allowed.",
        })
    if _MODULE_BLOCK_PATTERN.search(main_tf):
        return json.dumps({
            "passed": False,
            "stage": "preflight",
            "error": "Module blocks are not supported by this single-file validator.",
        })

    with tempfile.TemporaryDirectory(prefix="terraform-validation-") as temp_dir:
        configuration_path = Path(temp_dir) / "main.tf"
        configuration_path.write_text(main_tf, encoding="utf-8")

        try:
            init_result = subprocess.run(
                [
                    "terraform", "init", "-backend=false", "-get=false",
                    "-input=false", "-no-color",
                ],
                cwd=temp_dir,
                capture_output=True,
                text=True,
                timeout=_COMMAND_TIMEOUT_SECONDS,
                check=False,
            )
        except FileNotFoundError:
            logger.exception("terraform executable was not found")
            return json.dumps({
                "passed": False,
                "stage": "init",
                "error": "Terraform CLI was not found on PATH.",
            })
        except subprocess.TimeoutExpired:
            logger.exception("terraform init timed out")
            return json.dumps({
                "passed": False,
                "stage": "init",
                "error": f"terraform init exceeded {_COMMAND_TIMEOUT_SECONDS} seconds.",
            })

        if init_result.returncode != 0:
            return json.dumps({
                "passed": False,
                "stage": "init",
                "exit_code": init_result.returncode,
                "stdout": init_result.stdout,
                "stderr": init_result.stderr,
            })

        try:
            validate_result = subprocess.run(
                ["terraform", "validate", "-json"],
                cwd=temp_dir,
                capture_output=True,
                text=True,
                timeout=_COMMAND_TIMEOUT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired:
            logger.exception("terraform validate timed out")
            return json.dumps({
                "passed": False,
                "stage": "validate",
                "error": f"terraform validate exceeded {_COMMAND_TIMEOUT_SECONDS} seconds.",
            })

    try:
        validation_json = json.loads(validate_result.stdout)
    except json.JSONDecodeError:
        logger.error(
            "terraform validate returned non-JSON output",
            extra={"exit_code": validate_result.returncode},
        )
        return json.dumps({
            "passed": False,
            "stage": "validate",
            "exit_code": validate_result.returncode,
            "stdout": validate_result.stdout,
            "stderr": validate_result.stderr,
            "error": "Terraform validation output was not valid JSON.",
        })

    passed = validate_result.returncode == 0 and validation_json.get("valid") is True
    report = {
        "passed": passed,
        "stage": "complete" if passed else "validate",
        "init_exit_code": init_result.returncode,
        "init_stdout": init_result.stdout,
        "init_stderr": init_result.stderr,
        "validate_exit_code": validate_result.returncode,
        "validate_json": validation_json,
        "validate_stderr": validate_result.stderr,
    }
    logger.info(
        "terraform configuration validation completed",
        extra={"passed": passed, "validation_exit_code": validate_result.returncode},
    )
    return json.dumps(report)
