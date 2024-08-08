from dataclasses import dataclass


@dataclass
class MongoContext:
    stage_name: str
    removal_policy: str  # aws_cdk.core.RemovalPolicy (RETAIN|DESTROY|SNAPSHOT)
    instance_type: str  # aws_ec2.InstanceType i.e. t3.medium
    subnet_type: str  # aws_ec2.SubnetType (ISOLATED|PRIVATE|PUBLIC)
    instances: int
    master_username: str
