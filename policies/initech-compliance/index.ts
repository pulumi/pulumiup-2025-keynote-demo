import * as aws from "@pulumi/aws";
import { PolicyPack, validateResourceOfType } from "@pulumi/policy";

new PolicyPack("initech-compliance", {
    policies: [
        {
            name: "check-required-tags",
            description: "Ensures all taggable AWS resources has the required tags.",
            enforcementLevel: "advisory",
            configSchema: {
                properties: {
                    requiredTags: {
                        type: "array",
                        items: { type: "string" },
                    },
                },
            },
            validateResource: (args, reportViolation) => {
                // If tags are configured, and this resource is taggable, check it.
                if (isTaggable(args.type)) {
                    const tags = args.props["tags"];
                    const config = args.getConfig<RequiredTagsPolicyConfig>();
                    for (const rt of config.requiredTags || []) {
                        if (!tags || !tags[rt]) {
                            reportViolation(`Taggable resource is missing required tag '${rt}'`);
                        }
                    }
                }
            },
        },
        {
            name: "disallow-massive-ecs-tasks",
            description: "Disallows ECS tasks with more than a certain amount of max CPU and/or memory.",
            enforcementLevel: "mandatory",
            configSchema: {
                properties: {
                    maxCpu: {
                        type: "integer",
                        minimum: 0,
                    },
                    maxMemory: {
                        type: "integer",
                        minimum: 0,
                    },
                }
            },
            validateResource: validateResourceOfType(aws.ecs.TaskDefinition, (props, args, reportViolation) => {
                const config = args.getConfig<DisallowMassiveEcsTasksConfig>();
                const cpu = props.cpu;
                const maxCpu = config.maxCpu;
                if (cpu && maxCpu !== undefined && parseInt(cpu) > maxCpu) {
                    reportViolation(`ECS task uses too much CPU (${cpu} > ${maxCpu})`);
                }
                const memory = props.memory;
                const maxMemory = config.maxMemory;
                if (memory && maxMemory !== undefined && parseInt(memory) > maxMemory) {
                    reportViolation(`ECS task uses too much memory (${memory} > ${maxMemory})`);
                }
            }),
        },
    ],
});

interface RequiredTagsPolicyConfig {
    requiredTags?: string;
}

interface DisallowMassiveEcsTasksConfig {
    maxCpu?: number;
    maxMemory?: number;
}

/**
 * isTaggable returns true if the given resource type is an AWS resource that supports tags.
 */
export function isTaggable(t: string): boolean {
    return (taggableResourceTypes.indexOf(t) !== -1);
}

// taggableResourceTypes is a list of known AWS type tokens that are taggable.
const taggableResourceTypes = [
    // At Initech, we only enforce tagging currently for ECS Clusters and Services.
    "aws:ecs/cluster:Cluster",
    "aws:ecs/service:Service",

    // Once we've all finished our TPS reports, we should come back and tag everything:
    // "aws:accessanalyzer/analyzer:Analyzer",
    // "aws:acm/certificate:Certificate",
    // "aws:acmpca/certificateAuthority:CertificateAuthority",
    // "aws:alb/loadBalancer:LoadBalancer",
    // "aws:alb/targetGroup:TargetGroup",
    // "aws:apigateway/apiKey:ApiKey",
    // "aws:apigateway/clientCertificate:ClientCertificate",
    // "aws:apigateway/domainName:DomainName",
    // "aws:apigateway/restApi:RestApi",
    // "aws:apigateway/stage:Stage",
    // "aws:apigateway/usagePlan:UsagePlan",
    // "aws:apigateway/vpcLink:VpcLink",
    // "aws:applicationloadbalancing/loadBalancer:LoadBalancer",
    // "aws:applicationloadbalancing/targetGroup:TargetGroup",
    // "aws:appmesh/mesh:Mesh",
    // "aws:appmesh/route:Route",
    // "aws:appmesh/virtualNode:VirtualNode",
    // "aws:appmesh/virtualRouter:VirtualRouter",
    // "aws:appmesh/virtualService:VirtualService",
    // "aws:appsync/graphQLApi:GraphQLApi",
    // "aws:athena/workgroup:Workgroup",
    // "aws:autoscaling/group:Group",
    // "aws:backup/plan:Plan",
    // "aws:backup/vault:Vault",
    // "aws:cfg/aggregateAuthorization:AggregateAuthorization",
    // "aws:cfg/configurationAggregator:ConfigurationAggregator",
    // "aws:cfg/rule:Rule",
    // "aws:cloudformation/stack:Stack",
    // "aws:cloudformation/stackSet:StackSet",
    // "aws:cloudfront/distribution:Distribution",
    // "aws:cloudhsmv2/cluster:Cluster",
    // "aws:cloudtrail/trail:Trail",
    // "aws:cloudwatch/eventRule:EventRule",
    // "aws:cloudwatch/logGroup:LogGroup",
    // "aws:cloudwatch/metricAlarm:MetricAlarm",
    // "aws:codebuild/project:Project",
    // "aws:codecommit/repository:Repository",
    // "aws:codepipeline/pipeline:Pipeline",
    // "aws:codepipeline/webhook:Webhook",
    // "aws:codestarnotifications/notificationRule:NotificationRule",
    // "aws:cognito/identityPool:IdentityPool",
    // "aws:cognito/userPool:UserPool",
    // "aws:datapipeline/pipeline:Pipeline",
    // "aws:datasync/agent:Agent",
    // "aws:datasync/efsLocation:EfsLocation",
    // "aws:datasync/locationSmb:LocationSmb",
    // "aws:datasync/nfsLocation:NfsLocation",
    // "aws:datasync/s3Location:S3Location",
    // "aws:datasync/task:Task",
    // "aws:dax/cluster:Cluster",
    // "aws:directconnect/connection:Connection",
    // "aws:directconnect/hostedPrivateVirtualInterfaceAccepter:HostedPrivateVirtualInterfaceAccepter",
    // "aws:directconnect/hostedPublicVirtualInterfaceAccepter:HostedPublicVirtualInterfaceAccepter",
    // "aws:directconnect/hostedTransitVirtualInterfaceAcceptor:HostedTransitVirtualInterfaceAcceptor",
    // "aws:directconnect/linkAggregationGroup:LinkAggregationGroup",
    // "aws:directconnect/privateVirtualInterface:PrivateVirtualInterface",
    // "aws:directconnect/publicVirtualInterface:PublicVirtualInterface",
    // "aws:directconnect/transitVirtualInterface:TransitVirtualInterface",
    // "aws:directoryservice/directory:Directory",
    // "aws:dlm/lifecyclePolicy:LifecyclePolicy",
    // "aws:dms/endpoint:Endpoint",
    // "aws:dms/replicationInstance:ReplicationInstance",
    // "aws:dms/replicationSubnetGroup:ReplicationSubnetGroup",
    // "aws:dms/replicationTask:ReplicationTask",
    // "aws:docdb/cluster:Cluster",
    // "aws:docdb/clusterInstance:ClusterInstance",
    // "aws:docdb/clusterParameterGroup:ClusterParameterGroup",
    // "aws:docdb/subnetGroup:SubnetGroup",
    // "aws:dynamodb/table:Table",
    // "aws:ebs/snapshot:Snapshot",
    // "aws:ebs/snapshotCopy:SnapshotCopy",
    // "aws:ebs/volume:Volume",
    // "aws:ec2/ami:Ami",
    // "aws:ec2/amiCopy:AmiCopy",
    // "aws:ec2/amiFromInstance:AmiFromInstance",
    // "aws:ec2/capacityReservation:CapacityReservation",
    // "aws:ec2/customerGateway:CustomerGateway",
    // "aws:ec2/defaultNetworkAcl:DefaultNetworkAcl",
    // "aws:ec2/defaultRouteTable:DefaultRouteTable",
    // "aws:ec2/defaultSecurityGroup:DefaultSecurityGroup",
    // "aws:ec2/defaultSubnet:DefaultSubnet",
    // "aws:ec2/defaultVpc:DefaultVpc",
    // "aws:ec2/defaultVpcDhcpOptions:DefaultVpcDhcpOptions",
    // "aws:ec2/eip:Eip",
    // "aws:ec2/fleet:Fleet",
    // "aws:ec2/instance:Instance",
    // "aws:ec2/internetGateway:InternetGateway",
    // "aws:ec2/keyPair:KeyPair",
    // "aws:ec2/launchTemplate:LaunchTemplate",
    // "aws:ec2/natGateway:NatGateway",
    // "aws:ec2/networkAcl:NetworkAcl",
    // "aws:ec2/networkInterface:NetworkInterface",
    // "aws:ec2/placementGroup:PlacementGroup",
    // "aws:ec2/routeTable:RouteTable",
    // "aws:ec2/securityGroup:SecurityGroup",
    // "aws:ec2/spotInstanceRequest:SpotInstanceRequest",
    // "aws:ec2/subnet:Subnet",
    // "aws:ec2/vpc:Vpc",
    // "aws:ec2/vpcDhcpOptions:VpcDhcpOptions",
    // "aws:ec2/vpcEndpoint:VpcEndpoint",
    // "aws:ec2/vpcEndpointService:VpcEndpointService",
    // "aws:ec2/vpcPeeringConnection:VpcPeeringConnection",
    // "aws:ec2/vpcPeeringConnectionAccepter:VpcPeeringConnectionAccepter",
    // "aws:ec2/vpnConnection:VpnConnection",
    // "aws:ec2/vpnGateway:VpnGateway",
    // "aws:ec2clientvpn/endpoint:Endpoint",
    // "aws:ec2transitgateway/routeTable:RouteTable",
    // "aws:ec2transitgateway/transitGateway:TransitGateway",
    // "aws:ec2transitgateway/vpcAttachment:VpcAttachment",
    // "aws:ec2transitgateway/vpcAttachmentAccepter:VpcAttachmentAccepter",
    // "aws:ecr/repository:Repository",
    // "aws:ecs/capacityProvider:CapacityProvider",
    // "aws:ecs/taskDefinition:TaskDefinition",
    // "aws:efs/fileSystem:FileSystem",
    // "aws:eks/cluster:Cluster",
    // "aws:eks/fargateProfile:FargateProfile",
    // "aws:eks/nodeGroup:NodeGroup",
    // "aws:elasticache/cluster:Cluster",
    // "aws:elasticache/replicationGroup:ReplicationGroup",
    // "aws:elasticbeanstalk/application:Application",
    // "aws:elasticbeanstalk/applicationVersion:ApplicationVersion",
    // "aws:elasticbeanstalk/environment:Environment",
    // "aws:elasticloadbalancing/loadBalancer:LoadBalancer",
    // "aws:elasticloadbalancingv2/loadBalancer:LoadBalancer",
    // "aws:elasticloadbalancingv2/targetGroup:TargetGroup",
    // "aws:elasticsearch/domain:Domain",
    // "aws:elb/loadBalancer:LoadBalancer",
    // "aws:emr/cluster:Cluster",
    // "aws:fsx/lustreFileSystem:LustreFileSystem",
    // "aws:fsx/windowsFileSystem:WindowsFileSystem",
    // "aws:gamelift/alias:Alias",
    // "aws:gamelift/build:Build",
    // "aws:gamelift/fleet:Fleet",
    // "aws:gamelift/gameSessionQueue:GameSessionQueue",
    // "aws:glacier/vault:Vault",
    // "aws:glue/crawler:Crawler",
    // "aws:glue/job:Job",
    // "aws:glue/trigger:Trigger",
    // "aws:iam/role:Role",
    // "aws:iam/user:User",
    // "aws:inspector/resourceGroup:ResourceGroup",
    // "aws:kinesis/analyticsApplication:AnalyticsApplication",
    // "aws:kinesis/firehoseDeliveryStream:FirehoseDeliveryStream",
    // "aws:kinesis/stream:Stream",
    // "aws:kms/externalKey:ExternalKey",
    // "aws:kms/key:Key",
    // "aws:lambda/function:Function",
    // "aws:lb/loadBalancer:LoadBalancer",
    // "aws:lb/targetGroup:TargetGroup",
    // "aws:licensemanager/licenseConfiguration:LicenseConfiguration",
    // "aws:lightsail/instance:Instance",
    // "aws:mediaconvert/queue:Queue",
    // "aws:mediapackage/channel:Channel",
    // "aws:mediastore/container:Container",
    // "aws:mq/broker:Broker",
    // "aws:mq/configuration:Configuration",
    // "aws:msk/cluster:Cluster",
    // "aws:neptune/cluster:Cluster",
    // "aws:neptune/clusterInstance:ClusterInstance",
    // "aws:neptune/clusterParameterGroup:ClusterParameterGroup",
    // "aws:neptune/eventSubscription:EventSubscription",
    // "aws:neptune/parameterGroup:ParameterGroup",
    // "aws:neptune/subnetGroup:SubnetGroup",
    // "aws:opsworks/stack:Stack",
    // "aws:organizations/account:Account",
    // "aws:pinpoint/app:App",
    // "aws:qldb/ledger:Ledger",
    // "aws:ram/resourceShare:ResourceShare",
    // "aws:rds/cluster:Cluster",
    // "aws:rds/clusterEndpoint:ClusterEndpoint",
    // "aws:rds/clusterInstance:ClusterInstance",
    // "aws:rds/clusterParameterGroup:ClusterParameterGroup",
    // "aws:rds/clusterSnapshot:ClusterSnapshot",
    // "aws:rds/eventSubscription:EventSubscription",
    // "aws:rds/instance:Instance",
    // "aws:rds/optionGroup:OptionGroup",
    // "aws:rds/parameterGroup:ParameterGroup",
    // "aws:rds/securityGroup:SecurityGroup",
    // "aws:rds/snapshot:Snapshot",
    // "aws:rds/subnetGroup:SubnetGroup",
    // "aws:redshift/cluster:Cluster",
    // "aws:redshift/eventSubscription:EventSubscription",
    // "aws:redshift/parameterGroup:ParameterGroup",
    // "aws:redshift/snapshotCopyGrant:SnapshotCopyGrant",
    // "aws:redshift/snapshotSchedule:SnapshotSchedule",
    // "aws:redshift/subnetGroup:SubnetGroup",
    // "aws:resourcegroups/group:Group",
    // "aws:route53/healthCheck:HealthCheck",
    // "aws:route53/resolverEndpoint:ResolverEndpoint",
    // "aws:route53/resolverRule:ResolverRule",
    // "aws:route53/zone:Zone",
    // "aws:s3/bucket:Bucket",
    // "aws:s3/bucketObject:BucketObject",
    // "aws:sagemaker/endpoint:Endpoint",
    // "aws:sagemaker/endpointConfiguration:EndpointConfiguration",
    // "aws:sagemaker/model:Model",
    // "aws:sagemaker/notebookInstance:NotebookInstance",
    // "aws:secretsmanager/secret:Secret",
    // "aws:servicecatalog/portfolio:Portfolio",
    // "aws:sfn/activity:Activity",
    // "aws:sfn/stateMachine:StateMachine",
    // "aws:sns/topic:Topic",
    // "aws:sqs/queue:Queue",
    // "aws:ssm/activation:Activation",
    // "aws:ssm/document:Document",
    // "aws:ssm/maintenanceWindow:MaintenanceWindow",
    // "aws:ssm/parameter:Parameter",
    // "aws:ssm/patchBaseline:PatchBaseline",
    // "aws:storagegateway/cachesIscsiVolume:CachesIscsiVolume",
    // "aws:storagegateway/gateway:Gateway",
    // "aws:storagegateway/nfsFileShare:NfsFileShare",
    // "aws:storagegateway/smbFileShare:SmbFileShare",
    // "aws:swf/domain:Domain",
    // "aws:transfer/server:Server",
    // "aws:transfer/user:User",
    // "aws:waf/rateBasedRule:RateBasedRule",
    // "aws:waf/rule:Rule",
    // "aws:waf/ruleGroup:RuleGroup",
    // "aws:waf/webAcl:WebAcl",
    // "aws:wafregional/rateBasedRule:RateBasedRule",
    // "aws:wafregional/rule:Rule",
    // "aws:wafregional/ruleGroup:RuleGroup",
    // "aws:wafregional/webAcl:WebAcl",
    // "aws:workspaces/directory:Directory",
    // "aws:workspaces/ipGroup:IpGroup",
];
