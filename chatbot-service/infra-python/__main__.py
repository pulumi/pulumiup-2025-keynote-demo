import json
import pulumi
from pulumi import Config
import pulumi_aws as aws
import pulumi_container_app as container_app

# Read stack configuration
config = Config()
aws_region = Config("aws").require("region")
vpc_id = config.get("vpcId")
subnet_ids = config.get("publicSubnetIds")
alb_cert_arn = config.get("albCertificateArn")

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
)

# Export the URL of the deployed application
pulumi.export("url", chat_app.url)
