from typing import Union, List

from aws_cdk import aws_ec2 as ec2, core

from contexts.rse import RSEContext
from contexts.subnet import SubnetContext
from contexts.trading_api import TradingApiContext
from stacks import Stack


class VPCStack(Stack):
    @property
    def name(self):
        return "vpc"

    def __init__(
        self,
        scope: core.Construct,
        context: Union[TradingApiContext, RSEContext],
        subnet_context: List[SubnetContext],
        prefix="",
        **kwargs,
    ) -> None:
        super().__init__(scope, f"{prefix}{self.identification(context.stage_name)}", **kwargs)

        subnet_context: List[SubnetContext]
        # Create VPC using our subnet allocation plan
        self.vpc = ec2.Vpc(
            scope=self,
            id=f"{prefix}{self.identification(context.stage_name)}-vpc",
            cidr=context.vpc_subnet_cidr,
            enable_dns_hostnames=True,
            enable_dns_support=True,
            nat_gateways=1,
            subnet_configuration=[
                # https://tidalmigrations.com/subnet-builder/   note: you need to add every subnet 3 times
                ec2.SubnetConfiguration(name=x.name, subnet_type=ec2.SubnetType(x.type), cidr_mask=x.mask)
                for x in subnet_context
            ],
        )
