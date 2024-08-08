from aws_cdk import aws_elasticache as redis, aws_ec2 as ec2, aws_ssm as ssm, core

from contexts.redis import RedisContext
from stacks import Stack


class RedisStack(Stack):
    @property
    def name(self):
        return "redis"

    def __init__(self, scope: core.Construct, vpc, redis_context: RedisContext, **kwargs) -> None:
        super().__init__(scope, self.identification(redis_context.stage_name), **kwargs)

        redis_sg = ec2.SecurityGroup(
            self,
            f"{self.identification(redis_context.stage_name)}-security-group",
            security_group_name=f"{self.identification(redis_context.stage_name)}-security-group",
            vpc=vpc,
            description="Security group for Redis Cluster",
            allow_all_outbound=False,
        )
        redis_sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(6379), "redis access")
        subnet_group = redis.CfnSubnetGroup(
            self,
            f"{self.identification(redis_context.stage_name)}-subnet-group",
            subnet_ids=[subnet.subnet_id for subnet in vpc.isolated_subnets],
            description="subnet group for redis",
        )
        self.cluster = redis.CfnCacheCluster(
            self,
            f"{self.identification(redis_context.stage_name)}-redis",
            cache_node_type=redis_context.instance_type,
            engine="redis",
            num_cache_nodes=1,  # Note that we want just one node because of the locks currently
            cluster_name=f"{self.identification(redis_context.stage_name)}-redis-cluster",
            cache_subnet_group_name=subnet_group.ref,
            vpc_security_group_ids=[redis_sg.security_group_id],
            auto_minor_version_upgrade=True,
        )
        self.cluster.add_depends_on(subnet_group)
        ssm.StringParameter(
            self,
            "redis-endpoint",
            parameter_name=f"/{redis_context.stage_name}/redis-endpoint",
            string_value=self.cluster.attr_redis_endpoint_address,
        )
        self.address = self.cluster.attr_redis_endpoint_address
