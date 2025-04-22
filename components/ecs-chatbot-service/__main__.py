import json
import pulumi
import pulumi_aws as aws
import pulumi_random as random
from pulumi.provider.experimental import component_provider_host
from typing import Optional, TypedDict, Dict, Any


def _render_container_defs(
    image_uri: str,
    env: Dict[str, str],
    secrets: Dict[str, str],
    log_group_name: str,
) -> str:
    """
    Build the JSON container definition array for an ECS task.

    Args:
        image_uri: Full image URI (`111122223333.dkr.ecr.us-west-2.amazonaws.com/chatbot:1.2.0`)
        env:      Plain‑text environment variables  { "MODEL_NAME": "gpt-4o", ... }
        secrets:  Secrets Manager / SSM ARNs        { "OPENAI_API_KEY": "arn:aws:secretsmanager:..." }
        log_group_name: CloudWatch LogGroup name used by awslogs driver

    Returns:
        JSON string (list with one container spec) suitable for
        ecs.TaskDefinition.container_definitions.
    """

    def _kv(name: str, value: str) -> Dict[str, str]:
        return {"name": name, "value": value}

    def _secret(name: str, arn: str) -> Dict[str, str]:
        return {"name": name, "valueFrom": arn}

    container: Dict[str, Any] = {
        "name": "app",                  # must match Service load_balancer.containerName
        "image": image_uri,
        "essential": True,
        "portMappings": [{"containerPort": 80, "protocol": "tcp"}],
        "environment": [_kv(k, v) for k, v in env.items()],
        "secrets": [_secret(k, arn) for k, arn in secrets.items()],
        "logConfiguration": {
            "logDriver": "awslogs",
            "options": {
                "awslogs-group": log_group_name,
                "awslogs-region": "us-west-2",   # or use aws.get_region().name
                "awslogs-stream-prefix": "ecs"
            },
        },
    }

    # TaskDefinition expects *a JSON string* representing an array of container objects
    return json.dumps([container])

class ChatbotServiceArgs(TypedDict):
    image_uri: pulumi.Input[str]
    cpu: Optional[pulumi.Input[int]]
    memory: Optional[pulumi.Input[int]]
    desired_count: Optional[pulumi.Input[int]]
    vpc_id: Optional[pulumi.Input[str]]
    public_subnet_ids: Optional[pulumi.Input[list[str]]]
    env: Optional[dict[str, pulumi.Input[str]]]
    secrets: Optional[dict[str, pulumi.Input[str]]]
    enable_autoscaling: Optional[pulumi.Input[bool]]

class ChatbotService(pulumi.ComponentResource):
    endpoint: pulumi.Output[str]
    """The URL of the service."""

    def __init__(self, name,
                 args: ChatbotServiceArgs,
                 opts: pulumi.ResourceOptions = None):
        super().__init__("ecs-chatbot-service-component:index:EcsChatbotService", name, {}, opts)

        image_uri = args["image_uri"]
        vpc_id = args.get("vpc_id")
        public_subnet_id = args.get("public_subnet_ids")
        env = args.get("env", {})
        secrets = args.get("secrets", {})
        cpu = args.get("cpu", 256)
        memory = args.get("memory", 512)
        desired_count = args.get("desired_count", 1)
        enable_autoscaling = args.get("enable_autoscaling", False)

        # 1. Network + cluster (create or re‑use) -------------------------
        vpc = (aws.ec2.get_vpc(id=vpc_id) if vpc_id
               else aws.ec2.Vpc(f"{name}-vpc", cidr_block="10.0.0.0/16"))
        subnets = (public_subnet_id or
                   [aws.ec2.Subnet(f"{name}-subnet",
                                   vpc_id=vpc.id,
                                   cidr_block="10.0.1.0/24",
                                   map_public_ip_on_launch=True).id])

        cluster = aws.ecs.Cluster(f"{name}-cluster")

        # 2. IAM task role ------------------------------------------------
        task_role = aws.iam.Role(f"{name}-task-role",
            assume_role_policy=aws.iam.get_policy_document(
                statements=[{
                    "actions": ["sts:AssumeRole"],
                    "principals": [{"type":"Service","identifiers":["ecs-tasks.amazonaws.com"]}]
                }]
            ).json)

        # 3. Log group ----------------------------------------------------
        logs = aws.cloudwatch.LogGroup(f"{name}-logs", retention_in_days=14)

        # 4. Task definition ---------------------------------------------
        td = aws.ecs.TaskDefinition(f"{name}-td",
            family=name,
            cpu=str(cpu),
            memory=str(memory),
            network_mode="awsvpc",
            requires_compatibilities=["FARGATE"],
            execution_role_arn=task_role.arn,
            task_role_arn=task_role.arn,
            container_definitions=pulumi.Output.all(env, secrets).apply(
                lambda tpl: _render_container_defs(image_uri, tpl[0] or {}, tpl[1] or {}, logs.name))
        )

        # 5. Security group ----------------------------------------------
        sg = aws.ec2.SecurityGroup(f"{name}-sg",
            vpc_id=vpc.id,
            ingress=[{"protocol":"tcp","from_port":80,"to_port":80,"cidr_blocks":["0.0.0.0/0"]}],
            egress=[{"protocol":"-1","from_port":0,"to_port":0,"cidr_blocks":["0.0.0.0/0"]}])

        # 6. Load Balancer + target group --------------------------------
        alb = aws.lb.LoadBalancer(f"{name}-alb",
            security_groups=[sg.id],
            subnets=subnets)

        tg  = aws.lb.TargetGroup(f"{name}-tg", port=80, protocol="HTTP",
                                 target_type="ip", vpc_id=vpc.id)

        listener = aws.lb.Listener(f"{name}-listener",
            load_balancer_arn=alb.arn, port=80, default_actions=[{
                "type":"forward","target_group_arn":tg.arn
            }])

        # 7. Service ------------------------------------------------------
        svc = aws.ecs.Service(f"{name}-svc",
            cluster=cluster.arn,
            desired_count=desired_count,
            launch_type="FARGATE",
            network_configuration={
                "subnets": subnets,
                "security_groups": [sg.id],
                "assign_public_ip": True
            },
            load_balancers=[{
                "targetGroupArn": tg.arn,
                "containerName": "app",
                "containerPort": 80
            }],
            task_definition=td.arn,
        )

        # 8. Optional autoscaling ----------------------------------------
        if enable_autoscaling:
            aws.appautoscaling.Target(f"{name}-asg-target",
                max_capacity=5, min_capacity=1,
                resource_id=svc.id.apply(lambda id_: f"service/{cluster.name}/{id_.split('/')[-1]}"),
                scalable_dimension="ecs:service:DesiredCount",
                service_namespace="ecs")
            # …plus CPU/memory scaling policies…

        # Outputs
        self.endpoint = alb.dns_name.apply(lambda dns: f"http://{dns}/chat")
        self.register_outputs({"endpoint": self.endpoint})

if __name__ == "__main__":
    component_provider_host(
        name="ecs-chatbot-service-component", components=[ChatbotService],
    )
