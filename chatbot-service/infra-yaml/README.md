# Chatbot Container App Template

This template deploys a containerized chatbot application to AWS ECS Fargate with an Application Load Balancer using the ContainerApp component.

## Features

- Deploys containerized chatbot applications to AWS ECS Fargate
- Creates or reuses VPC and subnets
- Sets up an Application Load Balancer
- Configures CloudWatch logging
- Supports environment variables and secrets
- Automatic container image building and pushing to ECR
- Secure handling of OpenAI API key
- Resource tagging with owner information
- ECS service metrics dashboard access

## Usage

1. Create a new project using this template:
   ```bash
   pulumi new container-app
   ```

2. Configure your application:
   - Place your chatbot application code in the `app` directory
   - Update the configuration values as needed:
     ```bash
     pulumi config set aws:region us-west-2
     pulumi config set app_port 8080
     pulumi config set environment dev
     pulumi config set cpu 256
     pulumi config set memory 512
     pulumi config set desired_count 1
     pulumi config set owner "team-a"  # Optional: Set owner for resource tagging
     ```

3. Configure your OpenAI API key:
   ```bash
   pulumi config set --secret openai_api_key "your-openai-api-key"
   ```

4. Deploy your application:
   ```bash
   pulumi up
   ```

## Configuration Options

- `aws:region`: The AWS region to deploy into (default: us-west-2)
- `app_port`: The port your application listens on (default: 8080)
- `environment`: The environment name (default: dev)
- `cpu`: The CPU units for the Fargate task (default: 256)
- `memory`: The memory for the Fargate task in MB (default: 512)
- `desired_count`: The desired number of tasks to run (default: 1)
- `openai_api_key`: Your OpenAI API key (required, will be stored as a secret)
- `owner`: The owner of the resources (optional, used for tagging)

## Security

- The application is deployed in a VPC with restricted access
- Ingress traffic is limited to the VPC CIDR (10.0.0.0/16)
- Egress traffic is allowed for necessary outbound connections
- Secrets are stored in AWS Secrets Manager
- IAM roles follow the principle of least privilege

## Outputs

- `url`: The URL of the deployed chatbot application
- `metricsUrl`: The URL to the ECS service metrics dashboard 