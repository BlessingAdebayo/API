from aws_cdk import core, aws_route53 as r53

from stacks import Stack


class DNSStack(Stack):
    @property
    def name(self):
        return "route53-dns"

    def __init__(self, scope: core.Construct, stage_name: str, dns: str, **kwargs) -> None:
        super().__init__(scope, self.identification(stage_name), **kwargs)

        self.hosted_zone = r53.HostedZone(self, "hosted-zone", zone_name=dns)
