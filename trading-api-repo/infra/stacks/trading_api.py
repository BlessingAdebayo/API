from aws_cdk import (
    core,
    aws_ec2 as ec2,
    aws_iam as _iam,
)

from contexts.trading_api import TradingApiContext
from stacks.api import ApiStack


class TradingAPIStack(ApiStack):
    @property
    def name(self):
        return "trading-api"

    def __init__(
        self, scope: core.Construct, context: TradingApiContext, vpc, redis, mongo, script="run_on_startup.sh", **kwargs
    ):
        super().__init__(scope, self.identification(context.stage_name), **kwargs)
        self.context = context
        self.redis = redis
        self.mongo = mongo
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

    @staticmethod
    def subnet_selection(i):
        return ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC if i == 0 else ec2.SubnetType.PRIVATE)

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
            id=f"{self.context.stage_name}-trading-api-role",
            assumed_by=_iam.ServicePrincipal("ec2.amazonaws.com"),
            role_name=f"{self.context.stage_name}-trading-api-role",
            description=f"The trading api role for EC2 instances for the {self.context.stage_name}.",
            managed_policies=[
                _iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEC2ContainerRegistryReadOnly"),
                _iam.ManagedPolicy.from_aws_managed_policy_name("AWSKeyManagementServicePowerUser"),
                _iam.ManagedPolicy.from_aws_managed_policy_name("SecretsManagerReadWrite"),
                _iam.ManagedPolicy.from_aws_managed_policy_name("AmazonElastiCacheFullAccess"),
                _iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore"),
                _iam.ManagedPolicy.from_managed_policy_name(
                    self, "KeyManagementServiceSigningPolicy", "AWSKeyManagementServiceSigningPolicy"
                ),  # This is not an AWS managed policy
            ],
        )
