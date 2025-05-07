# 🚀 ContainerApp Component

> A powerful Pulumi component that deploys containerized applications to AWS ECS Fargate with an Application Load Balancer.

---

## ✨ Key Features

* **Container Deployment**
  * Deploys to AWS ECS Fargate
  * Automatic container image building
  * ECR integration

* **Networking**
  * VPC and subnet management
  * Application Load Balancer setup
  * Secure networking configuration

* **Monitoring & Security**
  * CloudWatch logging
  * ECS service metrics dashboard
  * Environment variables & secrets management
  * Resource tagging

---

## 🛠️ Installation

```bash
# Install using GitHub token
GITHUB_TOKEN=$(gh auth token) pulumi package add github.com/pulumi/pulumiup-2025-keynote-demo/components/container-app
```

---

## 📝 Usage Examples

### Python Implementation

#### Using Application Code Directory
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

#### Using Existing Docker Image
```python
import * as pulumi from "@pulumi/pulumi";
import { ContainerApp } from "container-app";

const app = new ContainerApp("my-app", {
    image: "my-registry/my-app:latest",
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

### YAML Configuration

#### Using Application Code Directory
```yaml
name: my-app
runtime: yaml

packages:
  container-app: github.com/pulumi/pulumiup-2025-keynote-demo/components/container-app

config:
  aws:region:
    default: us-west-2
  app_port:
    default: 8080
  app_path:
    default: ./app
  environment:
    default: dev
  cpu:
    default: "256"
  memory:
    default: "512"
  desired_count:
    default: 2
  owner:
    default: "team-a"

resources:
  app:
    type: container-app:index:ContainerApp
    properties:
      appPath: ${app_path}
      appPort: ${app_port}
      cpu: ${cpu}
      memory: ${memory}
      env:
        ENVIRONMENT: ${environment}
      desiredCount: ${desired_count}
      owner: ${owner}
      secrets:
        API_KEY: ${api_key}

outputs:
  url: ${app.url}
  metricsUrl: ${app.metricsUrl}
```

#### Using Existing Docker Image
```yaml
name: my-app
runtime: yaml

packages:
  container-app: github.com/pulumi/pulumiup-2025-keynote-demo/components/container-app@v0.5.0

config:
  aws:region:
    default: us-west-2
  app_port:
    default: 8080
  image:
    default: my-registry/my-app:latest
  environment:
    default: dev
  cpu:
    default: "256"
  memory:
    default: "512"
  desired_count:
    default: 2
  owner:
    default: "team-a"

resources:
  app:
    type: container-app:index:ContainerApp
    properties:
      image: ${image}
      appPort: ${app_port}
      cpu: ${cpu}
      memory: ${memory}
      env:
        ENVIRONMENT: ${environment}
      desiredCount: ${desired_count}
      owner: ${owner}
      secrets:
        API_KEY: ${api_key}

outputs:
  url: ${app.url}
  metricsUrl: ${app.metricsUrl}
```

---

## 📚 API Documentation

### Input Parameters

| Parameter | Type | Required | Description |
|:---------:|:----:|:--------:|:------------|
| `app_path` | `string` | No* | Path to application code |
| `app_port` | `number` | **Yes** | Application port |
| `cpu` | `string` | No | CPU units (256 = 0.25 vCPU) |
| `memory` | `string` | No | Memory in MB |
| `desired_count` | `number` | No | Number of tasks |
| `vpc_id` | `string` | No | Optional VPC ID |
| `public_subnet_ids` | `string[]` | No | Optional subnet IDs |
| `alb_cert_arn` | `string` | No | ALB certificate ARN |
| `env` | `Record<string, string>` | No | Environment variables |
| `secrets` | `Record<string, string>` | No | AWS Secrets Manager secrets |
| `owner` | `string` | No | Resource owner tag |
| `image` | `string` | No* | Docker image |

> *Note: Either `app_path` or `image` must be provided, but not both.*

### Output Values

| Output | Type | Description |
|:------:|:----:|:------------|
| `url` | `string` | Application URL |
| `metricsUrl` | `string` | Metrics dashboard URL |

---

## 🔧 Resource Creation

The component creates the following AWS resources:

1. **Networking** `[VPC, Subnets, IGW]`
   - VPC (if not provided)
   - Public subnets
   - Internet Gateway
   - Route tables
   - Security groups

2. **Compute** `[ECS]`
   - ECS Cluster
   - ECS Task Definition
   - ECS Service

3. **Load Balancing** `[ALB]`
   - Application Load Balancer
   - Target Group
   - HTTP/HTTPS Listeners

4. **Security** `[IAM, Secrets]`
   - IAM Roles and Policies
   - Secrets in AWS Secrets Manager
   - Security Groups

5. **Monitoring** `[CloudWatch]`
   - CloudWatch Log Group

6. **Container Registry** `[ECR]`
   - ECR Repository
   - Docker image build and push

---

## 🔒 Security Considerations

* All resources are tagged with `Name` and optionally `Owner`
* Secrets are stored in AWS Secrets Manager
* IAM roles follow least privilege principle
* Network access is restricted to VPC CIDR
* HTTPS is supported when `alb_cert_arn` is provided

---

## 📄 License

This component is licensed under the MIT License.

---

*Made with ❤️ by the Pulumi team* 