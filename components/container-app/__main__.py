import json
import pulumi
from pulumi import ResourceOptions, Config
import pulumi_aws as aws
import pulumi_docker_build as docker_build
import base64
from typing import Optional, TypedDict, Dict, Any, List

class ContainerAppArgs(TypedDict):
    """Arguments for the ContainerApp component."""
    app_path: pulumi.Input[str]  # Path to the application code
    app_port: pulumi.Input[int]  # Port the app listens on
    cpu: Optional[pulumi.Input[int]]  # CPU units (256 = 0.25 vCPU)
    memory: Optional[pulumi.Input[int]]  # Memory in MB
    desired_count: Optional[pulumi.Input[int]]  # Number of tasks to run
    vpc_id: Optional[pulumi.Input[str]]  # Optional VPC ID
    public_subnet_ids: Optional[pulumi.Input[List[str]]]  # Optional subnet IDs
    alb_cert_arn: Optional[pulumi.Input[str]]  # Optional ALB certificate ARN
    env: Optional[Dict[str, pulumi.Input[str]]]  # Environment variables
    secrets: Optional[Dict[str, pulumi.Input[str]]]  # Secrets (ARNs)

class ContainerApp(pulumi.ComponentResource):
    """A component that deploys a containerized application to AWS ECS Fargate."""
    
    url: pulumi.Output[str]
    """The URL of the deployed application."""

    def __init__(self, name: str, args: ContainerAppArgs, opts: pulumi.ResourceOptions = None):
        super().__init__("container-app:index:ContainerApp", name, {}, opts)

        # Create a child resource options object
        child_opts = pulumi.ResourceOptions(parent=self)

        # Get configuration values with defaults
        app_path = args["app_path"]
        app_port = args["app_port"]
        cpu = args.get("cpu", 256)
        memory = args.get("memory", 512)
        desired_count = args.get("desired_count", 2)
        vpc_id = args.get("vpc_id")
        public_subnet_ids = args.get("public_subnet_ids")
        alb_cert_arn = args.get("alb_cert_arn")
        env = args.get("env", {})
        secrets = args.get("secrets", {})

        # Get AWS region from config
        aws_region = Config("aws").require("region")

        # (1) Networking: Use provided VPC/subnets or create new ones
        if vpc_id and public_subnet_ids:
            vpc = aws.ec2.get_vpc(id=vpc_id)
            subnets = public_subnet_ids
        else:
            # Create new VPC with two public subnets
            vpc = aws.ec2.Vpc(f"{name}-vpc",
                cidr_block="10.0.0.0/16",
                enable_dns_hostnames=True,
                enable_dns_support=True,
                tags={"Name": f"{name}-vpc"},
                opts=child_opts
            )
            igw = aws.ec2.InternetGateway(f"{name}-igw",
                vpc_id=vpc.id,
                tags={"Name": f"{name}-igw"},
                opts=child_opts
            )
            route_table = aws.ec2.RouteTable(f"{name}-public-rt",
                vpc_id=vpc.id,
                routes=[{"cidr_block": "0.0.0.0/0", "gateway_id": igw.id}],
                tags={"Name": f"{name}-public-rt"},
                opts=child_opts
            )
            azs = aws.get_availability_zones().names[:2]
            subnets = []
            for i, az in enumerate(azs):
                subnet = aws.ec2.Subnet(f"{name}-subnet-{i+1}",
                    vpc_id=vpc.id,
                    availability_zone=az,
                    cidr_block=f"10.0.{i}.0/24",
                    map_public_ip_on_launch=True,
                    tags={"Name": f"{name}-subnet-{i+1}"},
                    opts=child_opts
                )
                aws.ec2.RouteTableAssociation(f"{name}-subnet-{i+1}-assoc",
                    subnet_id=subnet.id,
                    route_table_id=route_table.id,
                    opts=child_opts
                )
                subnets.append(subnet.id)

        # (2) Security Group
        web_sg = aws.ec2.SecurityGroup(f"{name}-web-sg",
            vpc_id=vpc.id,
            description="Security group for web LB and ECS tasks",
            ingress=[
                {"protocol": "tcp", "from_port": 80, "to_port": 80, "cidr_blocks": ["0.0.0.0/0"]},
                {"protocol": "tcp", "from_port": 443, "to_port": 443, "cidr_blocks": ["0.0.0.0/0"]},
                {"protocol": "tcp", "from_port": 8080, "to_port": 8080, "self":True}
            ],
            egress=[
                {"protocol": "-1", "from_port": 0, "to_port": 0, "cidr_blocks": ["0.0.0.0/0"]}
            ],
            tags={"Name": f"{name}-web-sg"},
            opts=child_opts
        )

        # (3) ECS Cluster
        cluster = aws.ecs.Cluster(f"{name}-cluster",
            opts=child_opts
        )

        # (4) Load Balancer & Target Group
        alb = aws.lb.LoadBalancer(f"{name}-lb",
            security_groups=[web_sg.id],
            subnets=subnets,
            load_balancer_type="application",
            tags={"Name": f"{name}-lb"},
            opts=child_opts
        )
        target_group = aws.lb.TargetGroup(f"{name}-tg",
            port=app_port,
            protocol="HTTP",
            target_type="ip",
            vpc_id=vpc.id,
            health_check={
                "path": "/",
                "port": "traffic-port",
                "interval": 90,
                "timeout": 15,
                "healthy_threshold": 2,
                "unhealthy_threshold": 5,
                "matcher": "200"
            },
            tags={"Name": f"{name}-tg"},
            opts=child_opts
        )

        # (5) ALB Listeners
        if alb_cert_arn:
            https_listener = aws.lb.Listener(f"{name}-https-listener",
                load_balancer_arn=alb.arn,
                port=443,
                protocol="HTTPS",
                ssl_policy="ELBSecurityPolicy-2016-08",
                certificate_arn=alb_cert_arn,
                default_actions=[{"type": "forward", "target_group_arn": target_group.arn}],
                opts=child_opts
            )
            http_listener = aws.lb.Listener(f"{name}-http-listener",
                load_balancer_arn=alb.arn,
                port=80,
                protocol="HTTP",
                default_actions=[{
                    "type": "redirect",
                    "redirect": {"protocol": "HTTPS", "port": "443", "status_code": "HTTP_301"}
                }],
                opts=child_opts
            )
        else:
            http_listener = aws.lb.Listener(f"{name}-http-listener",
                load_balancer_arn=alb.arn,
                port=80,
                protocol="HTTP",
                default_actions=[{"type": "forward", "target_group_arn": target_group.arn}],
                opts=child_opts
            )

        # (6) IAM Roles
        task_exec_role = aws.iam.Role(f"{name}-task-exec-role",
            assume_role_policy=json.dumps({
                "Version": "2008-10-17",
                "Statement": [{
                    "Effect": "Allow",
                    "Principal": {"Service": "ecs-tasks.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }]
            }),
            opts=child_opts
        )
        aws.iam.RolePolicyAttachment(f"{name}-task-exec-policy",
            role=task_exec_role.name,
            policy_arn="arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy",
            opts=child_opts
        )

        # Add Secrets Manager policy
        secrets_policy = aws.iam.Policy(f"{name}-secrets-manager-policy",
            policy=pulumi.Output.all(secrets).apply(lambda s: json.dumps({
                "Version": "2012-10-17",
                "Statement": [{
                    "Effect": "Allow",
                    "Action": [
                        "secretsmanager:GetSecretValue"
                    ],
                    "Resource": list(s[0].values())  # Get all secret ARNs from the secrets dict
                }]
            })),
            opts=child_opts
        )

        # Attach the Secrets Manager policy to the task execution role
        aws.iam.RolePolicyAttachment(f"{name}-secrets-manager-policy-attachment",
            role=task_exec_role.name,
            policy_arn=secrets_policy.arn,
            opts=child_opts
        )

        # (7) Log Group
        log_group = aws.cloudwatch.LogGroup(f"{name}-logs",
            retention_in_days=7,
            tags={"Name": f"{name}-logs"},
            opts=child_opts
        )

        # (8) ECR Repository and Docker image
        repository = aws.ecr.Repository(f"{name}-repo",
            tags={"Name": f"{name}-repo"},
            force_delete=True,
            opts=child_opts
        )

        def get_registry_info(rid):
            creds = aws.ecr.get_credentials(registry_id=rid)
            decoded = base64.b64decode(creds.authorization_token).decode()
            parts = decoded.split(":")
            if len(parts) != 2:
                raise Exception("Invalid credentials")
            return docker_build.RegistryArgs(
                address=creds.proxy_endpoint,
                username=parts[0],
                password=parts[1]
            )

        registry = repository.registry_id.apply(get_registry_info)

        image = docker_build.Image(
            f"{name}-image",
            context=docker_build.BuildContextArgs(
                location=app_path,
            ),
            platforms=["linux/amd64"],
            push=True,
            registries=[registry],
            tags=[
                repository.repository_url.apply(lambda url: f"{url}:latest"),
            ],
            opts=child_opts
        )
        image_digest = image.digest

        # (9) ECS Task Definition
        container_def = pulumi.Output.all(
            repository.repository_url,
            image_digest,
            log_group.name,
            env,
            secrets
        ).apply(lambda args: json.dumps([{
            "name": "app",
            "image": f"{args[0]}@{args[1]}",
            "essential": True,
            "portMappings": [{"containerPort": int(app_port), "hostPort": int(app_port), "protocol": "tcp"}],
            "environment": [{"name": k, "value": v} for k, v in args[3].items()],
            "secrets": [{"name": k, "valueFrom": v} for k, v in args[4].items()],
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": args[2],
                    "awslogs-region": aws_region,
                    "awslogs-stream-prefix": "app"
                }
            }
        }]))

        task_def = aws.ecs.TaskDefinition(f"{name}-task",
            family=f"{name}-task",
            cpu=str(cpu),
            memory=str(memory),
            network_mode="awsvpc",
            requires_compatibilities=["FARGATE"],
            execution_role_arn=task_exec_role.arn,
            container_definitions=container_def,
            opts=child_opts
        )

        # (10) ECS Service
        service = aws.ecs.Service(f"{name}-service",
            cluster=cluster.arn,
            desired_count=desired_count,
            launch_type="FARGATE",
            task_definition=task_def.arn,
            network_configuration={
                "assign_public_ip": True,
                "subnets": subnets,
                "security_groups": [web_sg.id]
            },
            load_balancers=[{
                "target_group_arn": target_group.arn,
                "container_name": "app",
                "container_port": int(app_port)  # Ensure port is integer
            }],
            health_check_grace_period_seconds=120,  # Add grace period for health checks
            opts=ResourceOptions(
                parent=self,
                depends_on=[alb]
            )
        )

        # Output the load balancer endpoint URL
        self.url = alb.dns_name.apply(
            lambda dns: f"https://{dns}" if alb_cert_arn else f"http://{dns}"
        )
        self.register_outputs({"url": self.url})

if __name__ == "__main__":
    from pulumi.provider.experimental import component_provider_host
    component_provider_host(
        name="container-app",
        components=[ContainerApp],
    ) 