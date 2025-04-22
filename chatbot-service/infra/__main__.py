import json
import pulumi
from pulumi import Config
import pulumi_aws as aws
import pulumi_container_app as container_app

# Read stack configuration
config = Config()
aws_region = Config("aws").require("region")  # AWS region (must be set in Pulumi config) [oai_citation_attribution:2‡pulumi.com](https://www.pulumi.com/registry/packages/aws/how-to-guides/aws-py-fargate/#:~:text=2,region)
vpc_id = config.get("vpcId")
subnet_ids = config.get("publicSubnetIds")
alb_cert_arn = config.get("albCertificateArn")  # Optional ACM certificate ARN for HTTPS

# Parse subnet IDs if provided
if subnet_ids:
    try:
        subnet_ids = json.loads(subnet_ids)
    except Exception:
        subnet_ids = [s.strip() for s in subnet_ids.split(",")]

# Store the open ai api key in secrets manager
openai_api_key = aws.secretsmanager.Secret("openai-api-key",
    description="OpenAI API Key for chat application",
    tags={"Name": "openai-api-key"}
)

aws.secretsmanager.SecretVersion("openai-api-key-version",
    secret_id=openai_api_key.id,
    secret_string=config.require_secret("openaiApiKey")
)

# Create the chat app using our component
chat_app = container_app.ContainerApp("chat-app",
    app_path="../app",  # Path to the application code
    app_port=8080,      # Port the app listens on
    vpc_id=vpc_id,      # Optional: use existing VPC
    public_subnet_ids=subnet_ids,  # Optional: use existing subnets
    alb_cert_arn=alb_cert_arn,  # Optional: enable HTTPS
    secrets={
        "OPENAI_API_KEY": openai_api_key.arn,
    },
    # Use default values for other parameters:
    # cpu=256,           # 0.25 vCPU
    # memory=512,        # 0.5 GB
    # desired_count=2,   # Number of tasks
)

# Export the URL of the deployed application
pulumi.export("url", chat_app.url)
