# Terraform EC2 Mumbai Plan

This plan details the steps to deploy an EC2 instance in the Mumbai region using Terraform. It includes resource identification, HCL structure, dependencies, and deployment steps.

## Resources
- EC2 instance in Mumbai

## HCL Structure
- provider "aws" { region = "ap-south-1" }
- resource "aws_instance" "mumbai_ec2" {
  ami = "ami-0abcdef1234567890"
  instance_type = "t2.micro"
  tags = { Name = "MumbaiEC2" }
}

## Dependencies
- AWS credentials configured
- Terraform installed

## Deployment Steps
1. Initialize Terraform: terraform init
2. Validate configuration: terraform validate
3. Plan deployment: terraform plan
4. Apply configuration: terraform apply

Ensure AWS credentials are set in environment variables or configuration files before applying.