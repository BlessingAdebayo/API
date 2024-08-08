import aws_cdk.core
from aws_cdk import aws_docdb as mongo, aws_ec2 as ec2, aws_ssm as ssm, core
from aws_cdk.aws_ec2 import InstanceType

from contexts.mongodb import MongoContext
from stacks import Stack


class MongoStack(Stack):
    def __init__(self, scope: core.Construct, vpc, mongo_context: MongoContext, **kwargs) -> None:
        super().__init__(scope, self.identification(mongo_context.stage_name), **kwargs)

        mongo_sg = ec2.SecurityGroup(
            self,
            f"{self.identification(mongo_context.stage_name)}-security-group",
            security_group_name="mongo-security-group",
            vpc=vpc,
            description="SG for Mongo Cluster",
            allow_all_outbound=True,
        )
        mongo_sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(27017), "Access mongo")

        cluster = mongo.DatabaseCluster(
            self,
            f"{self.identification(mongo_context.stage_name)}-mongo",
            master_user=mongo.Login(
                username=mongo_context.master_username,
                # password=mongo_context.password,
            ),
            instance_type=InstanceType(mongo_context.instance_type),
            instances=mongo_context.instances,
            vpc_subnets={"subnet_type": ec2.SubnetType(mongo_context.subnet_type)},
            vpc=vpc,
            removal_policy=aws_cdk.core.RemovalPolicy(mongo_context.removal_policy),
            security_group=mongo_sg,
        )
        cluster.add_rotation_single_user()  # Automatically rotate the cluster db admin password after 30 days.

        cluster.add_security_groups(mongo_sg)

        cluster.connections.allow_default_port_from_any_ipv4("Open to the world")

        self.address = cluster.cluster_endpoint.socket_address

        ssm.StringParameter(
            self,
            "mongo-address",
            parameter_name="/" + mongo_context.stage_name + "/mongo-address",
            string_value=self.address,
        )

    @property
    def name(self):
        return "mongo"
