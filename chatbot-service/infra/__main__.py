import json
import pulumi
from pulumi import ResourceOptions, Config
import pulumi_aws as aws
import pulumi_docker as docker
import pulumi_docker_build as docker_build
import base64

# Read stack configuration
config = Config()
aws_region = Config("aws").require("region")  # AWS region (must be set in Pulumi config) [oai_citation_attribution:2‡pulumi.com](https://www.pulumi.com/registry/packages/aws/how-to-guides/aws-py-fargate/#:~:text=2,region)
vpc_id_cfg = config.get("vpcId")
subnet_ids_cfg = config.get("publicSubnetIds")
alb_cert_arn = config.get("albCertificateArn")  # Optional ACM certificate ARN for HTTPS

# (1) Networking: Use provided VPC/subnets or create new ones
if vpc_id_cfg and subnet_ids_cfg:
    # Use existing VPC and subnets (expected that subnet_ids_cfg is a JSON list or comma-separated list)
    vpc_id = vpc_id_cfg
    # Parse subnet IDs from config (they might be stored as a JSON string in config)
    try:
        subnet_ids = json.loads(subnet_ids_cfg)
    except Exception:
        subnet_ids = [s.strip() for s in subnet_ids_cfg.split(",")]
    # Ensure we have a list of subnet IDs
    public_subnet_ids = subnet_ids
else:
    # No VPC provided – create a new VPC with two public subnets and internet gateway
    vpc = aws.ec2.Vpc("chat-vpc",
        cidr_block="10.0.0.0/16",
        enable_dns_hostnames=True,
        enable_dns_support=True,
        tags={"Name": "chat-vpc"}
    )
    igw = aws.ec2.InternetGateway("chat-igw",
        vpc_id=vpc.id,
        tags={"Name": "chat-igw"}
    )
    route_table = aws.ec2.RouteTable("chat-public-rt",
        vpc_id=vpc.id,
        routes=[{"cidr_block": "0.0.0.0/0", "gateway_id": igw.id}],
        tags={"Name": "chat-public-rt"}
    )
    # Get two available AZs in the region for subnets
    azs = aws.get_availability_zones().names[:2]
    public_subnet_ids = []
    for i, az in enumerate(azs):
        subnet = aws.ec2.Subnet(f"chat-subnet-{i+1}",
            vpc_id=vpc.id,
            availability_zone=az,
            cidr_block=f"10.0.{i}.0/24",
            map_public_ip_on_launch=True,  # auto-assign public IPs to instances (for public subnet)
            tags={"Name": f"chat-subnet-{i+1}"}
        )
        # Associate the subnet with the public route table (so it has internet access)
        aws.ec2.RouteTableAssociation(f"chat-subnet-{i+1}-assoc",
            subnet_id=subnet.id,
            route_table_id=route_table.id
        )
        public_subnet_ids.append(subnet.id)
    vpc_id = vpc.id

# Security Group for the ALB and ECS tasks: allow inbound HTTP/HTTPS, and all outbound
web_sg = aws.ec2.SecurityGroup("chat-web-sg",
    vpc_id=vpc_id,
    description="Security group for web LB and ECS tasks",
    ingress=[
        {"protocol": "tcp", "from_port": 80,  "to_port": 80,  "cidr_blocks": ["0.0.0.0/0"]},   # HTTP 
        {"protocol": "tcp", "from_port": 443, "to_port": 443, "cidr_blocks": ["0.0.0.0/0"]}   # HTTPS
    ],
    egress=[
        {"protocol": "-1", "from_port": 0, "to_port": 0, "cidr_blocks": ["0.0.0.0/0"]}
    ],
    tags={"Name": "chat-web-sg"}
)

# (2) ECS Cluster
cluster = aws.ecs.Cluster("chat-cluster", name="chat-cluster")

# (3) Load Balancer & Target Group
alb = aws.lb.LoadBalancer("chat-app-lb",
    security_groups=[web_sg.id],
    subnets=public_subnet_ids,
    load_balancer_type="application",
    tags={"Name": "chat-app-lb"}
)
target_group = aws.lb.TargetGroup("chat-app-tg",
    port=80,
    protocol="HTTP",
    target_type="ip",  # target is IP because tasks use awsvpc networking (Fargate)
    vpc_id=vpc_id,
    health_check={
        "path": "/",                # Use root path for health check (the app now has a dedicated health check endpoint here)
        "port": "8080",             # Match the container port
        "interval": 30,             # Check every 30 seconds
        "timeout": 5,               # 5 second timeout for health check
        "healthy_threshold": 2,     # Number of consecutive successful checks to be considered healthy
        "unhealthy_threshold": 3    # Number of consecutive failed checks to be considered unhealthy
    },
    tags={"Name": "chat-app-tg"}
)

# Listener(s) for the ALB
if alb_cert_arn:
    # If an ACM certificate is provided, set up an HTTPS listener
    https_listener = aws.lb.Listener("chat-https-listener",
        load_balancer_arn=alb.arn,
        port=443,
        protocol="HTTPS",
        ssl_policy="ELBSecurityPolicy-2016-08",  # AWS predefined SSL policy
        certificate_arn=alb_cert_arn,
        default_actions=[{"type": "forward", "target_group_arn": target_group.arn}]
    )
    # Optional: redirect HTTP to HTTPS
    http_listener = aws.lb.Listener("chat-http-listener",
        load_balancer_arn=alb.arn,
        port=80,
        protocol="HTTP",
        default_actions=[{
            "type": "redirect",
            "redirect": {"protocol": "HTTPS", "port": "443", "status_code": "HTTP_301"}
        }]
    )
else:
    # If no certificate, just create an HTTP listener forwarding to the target group
    http_listener = aws.lb.Listener("chat-http-listener",
        load_balancer_arn=alb.arn,
        port=80,
        protocol="HTTP",
        default_actions=[{"type": "forward", "target_group_arn": target_group.arn}]
    )

# (4) IAM Task Execution Role (for ECS tasks to use AWS services like ECR & CloudWatch Logs)
task_exec_role = aws.iam.Role("chat-task-exec-role",
    assume_role_policy=json.dumps({
        "Version": "2008-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "ecs-tasks.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    })
)
# Attach the AWS managed policy for ECS task execution (allows pulling images, logging, etc.)
aws.iam.RolePolicyAttachment("chat-task-exec-policy",
    role=task_exec_role.name,
    policy_arn="arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
)

# (5) CloudWatch Log Group for container logs
log_group = aws.cloudwatch.LogGroup("chat-app-loggrp", 
    retention_in_days=7,
    tags={"Name": "chat-app-logs"}
)

# (6) ECR Repository and Docker image build
repository = aws.ecr.Repository("chat-app-repo", tags={"Name": "chat-app-repo"}, force_delete=True)
# -----------------------------------------------------------------------
# ECR login helper: fetch a short‑lived auth token so Pulumi's Docker
# provider can push the image to this account's private registry.
# -----------------------------------------------------------------------
def get_registry_info(rid):
    creds = aws.ecr.get_credentials(registry_id=rid)
    decoded = base64.b64decode(creds.authorization_token).decode()
    parts = decoded.split(":")
    if len(parts) != 2:
        raise Exception("Invalid credentials")
    return docker_build.RegistryArgs(
        address=creds.proxy_endpoint, username=parts[0], password=parts[1]
    )

registry = repository.registry_id.apply(get_registry_info)

image = docker_build.Image(
    "chat-app-image",
    context=docker_build.BuildContextArgs(
        location="../app",
    ),
    platforms=["linux/amd64"],  # Specify platform to match AWS Fargate
    push=True,
    registries=[registry],
    tags=[
        repository.repository_url.apply(lambda url: f"{url}:v2"),  # Updated tag to force a rebuild
    ]
)
# The `digest` output includes the image digest, ensuring ECS picks up updated images
image_digest = image.digest

# (7) ECS Task Definition for the chat app container
# Define the container using the image from ECR and environment variables for secrets.
# Create a container definition that properly handles Output values
container_def = pulumi.Output.all(
    repository.repository_url, 
    image_digest,
    log_group.name,
    config.require_secret("openaiApiKey")
).apply(lambda args: json.dumps([{
    "name": "chat-app",
    "image": f"{args[0]}@{args[1]}",  # Full ECR image URI with digest
    "essential": True,
    "portMappings": [{"containerPort": 8080, "hostPort": 8080, "protocol": "tcp"}],
    "environment": [
        {"name": "OPENAI_API_KEY", "value": args[3]}
    ],
    # Enable CloudWatch logging for the container
    "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
            "awslogs-group": args[2],
            "awslogs-region": aws_region,
            "awslogs-stream-prefix": "chat-app"
        }
    }
}]))
task_def = aws.ecs.TaskDefinition("chat-app-task",
    family="chat-app-task",  # family name for the task definition
    cpu="256",      # 0.25 vCPU
    memory="512",   # 0.5 GB
    network_mode="awsvpc",
    requires_compatibilities=["FARGATE"],
    execution_role_arn=task_exec_role.arn,
    container_definitions=container_def  # JSON definition for containers
)

# (8) ECS Service to run the task on Fargate, behind the ALB
service = aws.ecs.Service("chat-app-service",
    cluster=cluster.arn,
    desired_count=2,  # run two tasks (for high availability)
    launch_type="FARGATE",
    task_definition=task_def.arn,
    network_configuration={
        "assign_public_ip": True,             # assign public IP to tasks (so they can reach the internet)
        "subnets": public_subnet_ids,         # run tasks in the public subnets
        "security_groups": [web_sg.id]        # attach the same security group (allows outbound internet)
    },
    load_balancers=[{
        "target_group_arn": target_group.arn,
        "container_name": "chat-app",
        "container_port": 8080
    }],
    opts=ResourceOptions(depends_on=[alb])  # ensure LB is created before service
)

# Output the load balancer endpoint URL
endpoint_url = alb.dns_name.apply(
    lambda dns: f"https://{dns}" if alb_cert_arn else f"http://{dns}"
)
pulumi.export("url", endpoint_url)
