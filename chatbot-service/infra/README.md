# Chatbot Infrastructure

This repository contains the Pulumi infrastructure code for deploying the chat API to ECS Fargate.

## Description

Pulumi stack that deploys the chat API to ECS Fargate. This infrastructure code manages the AWS resources needed for running the chatbot service in a scalable and managed environment.

## Requirements

- Python 3.11+
- Pulumi CLI
- AWS credentials configured

## Usage

```bash
# Install dependencies
pulumi install

# Preview changes
pulumi preview

# Deploy infrastructure
pulumi up
```

## Components

- AWS ECS Fargate for container orchestration
- AWS networking components (VPC, subnets, etc.)
- Container registry and deployment pipeline

