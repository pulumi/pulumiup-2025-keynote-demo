# ContainerApp Component

A Pulumi component that deploys containerized applications to AWS ECS Fargate with an Application Load Balancer.

## Features

- Deploys containerized applications to AWS ECS Fargate
- Creates or reuses VPC and subnets
- Sets up an Application Load Balancer
- Configures CloudWatch logging
- Supports environment variables and secrets
- Automatic container image building and pushing to ECR
- Resource tagging with owner information
- ECS service metrics dashboard access
- Secure networking with restricted VPC access

## Installation

```bash
pulumi package install container-app
```

## Usage

```python
import * as pulumi from "@pulumi/pulumi";
import { ContainerApp } from "container-app";

const app = new ContainerApp("my-app", {
    appPath: "./app",
    appPort: 8080,
    cpu: "256",
    memory: "512",
    desiredCount: 2,
    env: {
        ENVIRONMENT: "dev",
    },
    secrets: {
        API_KEY: "my-secret-key",
    },
    owner: "team-a",
});

export const url = app.url;
export const metricsUrl = app.metricsUrl;
```

## API Documentation

### Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `app_path` | `string` | Yes | Path to the application code directory |
| `app_port` | `number` | Yes | Port the application listens on |
| `cpu` | `string` | No | CPU units for the container (256 = 0.25 vCPU, default: "256") |
| `memory` | `string` | No | Memory in MB for the container (default: "512") |
| `desired_count` | `number` | No | Number of tasks to run (default: 2) |
| `vpc_id` | `string` | No | Optional VPC ID to use instead of creating a new one |
| `public_subnet_ids` | `string[]` | No | Optional subnet IDs to use instead of creating new ones |
| `alb_cert_arn` | `string` | No | Optional ALB certificate ARN for HTTPS |
| `env` | `Record<string, string>` | No | Environment variables for the container |
| `secrets` | `Record<string, string>` | No | Secrets to be stored in AWS Secrets Manager |
| `owner` | `string` | No | Owner tag value for all resources |

### Outputs

| Name | Type | Description |
|------|------|-------------|
| `url` | `string` | The URL of the deployed application |
| `metricsUrl` | `string` | The URL to the ECS service metrics dashboard |

## Resource Creation

The component creates the following AWS resources:

1. **Networking**
   - VPC (if not provided)
   - Public subnets (if not provided)
   - Internet Gateway
   - Route tables
   - Security groups

2. **Compute**
   - ECS Cluster
   - ECS Task Definition
   - ECS Service

3. **Load Balancing**
   - Application Load Balancer
   - Target Group
   - HTTP/HTTPS Listeners

4. **Security**
   - IAM Roles and Policies
   - Secrets in AWS Secrets Manager
   - Security Groups

5. **Monitoring**
   - CloudWatch Log Group

6. **Container Registry**
   - ECR Repository
   - Docker image build and push

## Security Considerations

- All resources are tagged with `Name` and optionally `Owner`
- Secrets are stored in AWS Secrets Manager
- IAM roles follow least privilege principle
- Network access is restricted to VPC CIDR
- HTTPS is supported when `alb_cert_arn` is provided

## License

This component is licensed under the MIT License. 