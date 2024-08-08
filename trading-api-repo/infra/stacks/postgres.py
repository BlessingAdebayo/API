import uuid

from aws_cdk import aws_ec2 as ec2, aws_rds as rds, core, aws_ssm as ssm
from aws_cdk.core import SecretValue

from stacks import Stack


class PostgresStack(Stack):
    @property
    def name(self):
        return "postgres"

    def __init__(self, scope: core.Construct, stage_name: str, vpc: ec2.Vpc, **kwargs):
        super().__init__(scope, self.identification(stage_name), **kwargs)

        self.sg_postgres = ec2.SecurityGroup(
            self,
            f"{self.identification(stage_name)}-security-group",
            security_group_name=f"{self.identification(stage_name)}-security-group-firewall",
            vpc=vpc,
            description=f"security group for {self.identification(stage_name)}",
            allow_all_outbound=False,
        )
        self.sg_postgres.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(5432), "Postgres Access")

        cluster = rds.ServerlessCluster(
            self,
            "psqlserverless",
            engine=rds.DatabaseClusterEngine.AURORA_POSTGRESQL,
            parameter_group=rds.ParameterGroup.from_parameter_group_name(
                self, "ParameterGroup", "default.aurora-postgresql10"
            ),
            vpc=vpc,
            vpc_subnets=dict(subnet_type=ec2.SubnetType.ISOLATED),
            security_groups=[self.sg_postgres],
            credentials=rds.Credentials.from_password(
                username="postgres", password=SecretValue(password := str(uuid.uuid4()))
            ),
        )
        cluster.connections.allow_from_any_ipv4(port_range=ec2.Port.tcp(5432))
        ssm.StringParameter(
            self,
            "postgres-password",
            parameter_name=f"/{stage_name}/postgres-password",
            string_value=password,
        )
        ssm.StringParameter(
            self,
            "postgres-endpoint",
            parameter_name=f"/{stage_name}/postgres-endpoint",
            string_value=str(cluster.cluster_endpoint),
        )
