from aws_cdk import core, aws_ec2 as ec2, aws_iam as _iam, aws_ssm as ssm
from aws_cdk.aws_ec2 import SubnetType

from contexts.rse import RSEContext
from contexts.subnet import SubnetContext
from stacks.api import ApiStack


class RSEStack(ApiStack):
    @property
    def name(self):
        return "rse"

    def __init__(
        self,
        scope: core.Construct,
        context: RSEContext,
        vpc,
        postgres,
        script="rse_run_on_startup.sh",
        **kwargs,
    ):
        super().__init__(scope, self.identification(context.stage_name), **kwargs)
        self.context = context
        self.postgres = postgres
        self.script = script
        self.security_group, self.bastion_group = self.define_security_group(vpc)
        self.role = self.create_role()
        self.api_instances = self.define_instances(
            context.instance_type,
            vpc,
            n=context.nr_instances,
            security_group=self.security_group,
            bastion_security_group=self.bastion_group,
            access_key_name=context.access_key_name,
            role=self.role,
        )
        self.lb = self.define_load_balancer(dns=context.dns, vpc=vpc, cert_arn=context.cert_arn)
        self.algorithm_nodes_network = self.add_algo_node_vpc(context.subnetwork_base_algonodes)

    def add_algo_node_vpc(self, base: int):
        assert 22 >= base >= 16, "choose algorithm node subnet base between 22 and 16 (lower means larger)"

        subsequent = [base + 6, base + 4, base + 2]
        subnet_context = [
            SubnetContext(
                SubnetType.PRIVATE if i != 0 else SubnetType.PUBLIC,
                name=f"rse-algo-subnet-{self.context.stage_name}-{x}",
                mask=x,
            )
            for i, x in enumerate(subsequent)
        ]

        vpc = ec2.Vpc(
            scope=self,
            id=f"rse-algonodes-{self.identification(self.context.stage_name)}-vpc",
            cidr=f"10.0.0.0/{base}",
            enable_dns_hostnames=False,
            enable_dns_support=False,
            nat_gateways=1,
            subnet_configuration=[
                # https://tidalmigrations.com/subnet-builder/   note: you need to add every subnet 3 times
                ec2.SubnetConfiguration(name=x.name, subnet_type=ec2.SubnetType(x.type), cidr_mask=x.mask)
                for x in subnet_context
            ],
        )

        ssm.StringParameter(
            self,
            f"algo-nodes-vpc-id-{self.context.stage_name}",
            parameter_name=f"/{self.context.stage_name}/algo-nodes-vpc-id",
            string_value=vpc.vpc_id,
        )

        ssm.StringListParameter(
            self,
            f"algo-nodes-subnet-id-{self.context.stage_name}",
            parameter_name=f"/{self.context.stage_name}/algo-nodes-subnet-ids",
            string_list_value=[x.subnet_id for x in vpc.private_subnets],
        )

        return vpc

    @staticmethod
    def subnet_selection(i):
        return ec2.SubnetSelection(subnet_name="Public" if i == 0 else "Apps")

    def transform_user_data(self, i):
        with open(self.script) as f:
            user_data: str = f.read()
            user_data = user_data.replace("{%STAGE_NAME%}", self.context.stage_name)
            user_data = user_data.replace("{%NODE_NUMBER%}", str(i))
            user_data = user_data.replace("{%IMAGE_TAG%}", self.context.image_tag)
        return user_data

    def create_role(self):
        return _iam.Role(
            scope=self,
            id=f"{self.context.stage_name}-rse-role",
            assumed_by=_iam.ServicePrincipal("ec2.amazonaws.com"),
            role_name=f"{self.context.stage_name}-rse-role",
            description=f"The rse role for EC2 instances for the {self.context.stage_name}.",
            managed_policies=[
                _iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEC2ContainerRegistryReadOnly"),
                _iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEC2FullAccess "),
                _iam.ManagedPolicy.from_aws_managed_policy_name("AmazonRDSFullAccess"),
                _iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3ReadOnlyAccess "),
                _iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore"),
                _iam.ManagedPolicy.from_aws_managed_policy_name("SecretsManagerReadWrite"),
            ],
        )
