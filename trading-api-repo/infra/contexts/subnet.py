from dataclasses import dataclass

from aws_cdk import aws_ec2 as ec2


@dataclass
class SubnetContext:
    type: ec2.SubnetType
    name: str
    mask: int
