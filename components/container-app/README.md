# Container App Component

A Pulumi component that deploys a containerized application to AWS ECS Fargate with an Application Load Balancer.

## Features

- Deploys containerized applications to AWS ECS Fargate
- Creates or reuses VPC and subnets
- Sets up an Application Load Balancer with optional HTTPS support
- Configures CloudWatch logging
- Supports environment variables and secrets
- Automatic container image building and pushing to ECR

## Usage

```python
from pulumi import Config
from components.container_app import ContainerApp

config = Config()
openai_api_key = config.require_secret("openaiApiKey")

app = ContainerApp("my-app",
    app_path="../app",  # Path to your application code
    app_port=8080,      # Port your app listens on
    env={
        "ENVIRONMENT": "production",
    },
    secrets={
        "OPENAI_API_KEY": openai_api_key,
    },
    # Optional parameters with defaults:
    # cpu=256,           # 0.25 vCPU
    # memory=512,        # 0.5 GB
    # desired_count=2,   # Number of tasks
    # vpc_id=None,       # Use existing VPC
    # public_subnet_ids=None,  # Use existing subnets
    # alb_cert_arn=None,  # Enable HTTPS
)

# Get the URL of the deployed application
pulumi.export("url", app.url)
```

## Required Configuration

- AWS region must be set in Pulumi config:
  ```bash
  pulumi config set aws:region us-west-2
  ```

## Optional Configuration

- VPC ID and subnet IDs if using existing infrastructure
- ALB certificate ARN for HTTPS support
- Environment variables and secrets
- CPU, memory, and desired task count

## Outputs

- `url`: The URL of the deployed application (HTTP or HTTPS depending on certificate configuration) 