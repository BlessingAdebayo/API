from abc import abstractmethod

from aws_cdk import (
    aws_ec2 as ec2,
    aws_elasticloadbalancingv2 as load_balancer,
    aws_certificatemanager as cert,
)
from aws_cdk.aws_ec2 import MachineImage
from stacks import Stack


class ApiStack(Stack):
    @property
    def name(self):
        return "api"

    def define_instances(
        self, instance_type, vpc, n, security_group, bastion_security_group, access_key_name: str, role
    ):

        instances = []
        for i in range(n + 1):
            node_type_name = "bastion" if i == 0 else "node"
            instance_name = f"{self.identification(self.context.stage_name)}-{i}-{node_type_name}"

            user_data = self.transform_user_data(i)

            instances.append(
                ec2.Instance(
                    scope=self,
                    id=f"{self.identification(self.context.stage_name)}-ec2-{i}",
                    instance_type=ec2.InstanceType("t2.micro" if i == 0 else instance_type),
                    machine_image=MachineImage.generic_linux(
                        # if we want to run outide eu-west-1 we need more ami's here
                        {"eu-west-1": "ami-0a8e758f5e873d1c1"}
                    ),
                    vpc=vpc,
                    key_name=access_key_name,  # has to be manually created in frontend
                    vpc_subnets=self.subnet_selection(i),
                    instance_name=instance_name,
                    security_group=security_group if i > 0 else bastion_security_group,
                    user_data=ec2.UserData.custom(user_data) if i > 0 else None,
                    role=role,
                    block_devices=self.get_ec2_block_devices(),
                )
            )
        return instances

    def define_load_balancer(self, dns, vpc, cert_arn="", email=False):
        security_group = ec2.SecurityGroup(
            self,
            f"{self.identification(self.context.stage_name)}-security-group-lb",
            security_group_name=f"{self.identification(self.context.stage_name)}-security-group-firewall-lb",
            vpc=vpc,
            description=f"security group for {self.identification(self.context.stage_name)}",
            allow_all_outbound=True,
        )
        security_group.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(443), "HTTPS Access")

        lb = load_balancer.ApplicationLoadBalancer(
            scope=self,
            id=f"{self.identification(self.context.stage_name)}-lb",
            security_group=security_group,
            vpc=vpc,
            internet_facing=True,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            load_balancer_name=f"{self.identification(self.context.stage_name)}-lb",
        )
        if email:
            # this does email validation
            certificate = cert.Certificate(
                self, id=f"{self.identification(self.context.stage_name)}-certificate", domain_name=dns
            )
        else:
            # this is the certificate you made according to the readme
            assert len(cert_arn) > 0, "if email validation is false you need to pass a certificate arn"
            certificate = cert.Certificate.from_certificate_arn(
                self, id=f"{self.identification(self.context.stage_name)}-certificate", certificate_arn=cert_arn
            )
        listener = lb.add_listener(
            f"{self.identification(self.context.stage_name)}-lb-listener",
            protocol=load_balancer.ApplicationProtocol.HTTPS,
            port=443,
            certificates=[certificate],
        )
        listener.connections.allow_default_port_from_any_ipv4("Open to the world")
        listener.add_targets(
            f"{self.identification(self.context.stage_name)}-lb-listener-targets",
            port=80,
            protocol=load_balancer.ApplicationProtocol.HTTP,
            targets=[load_balancer.InstanceTarget(x.instance_id) for i, x in enumerate(self.api_instances) if i > 0],
        )
        return lb

    def define_security_group(self, vpc):
        security_group = ec2.SecurityGroup(
            self,
            f"{self.identification(self.context.stage_name)}-security-group",
            security_group_name=f"{self.identification(self.context.stage_name)}-security-group-firewall",
            vpc=vpc,
            description=f"security group for {self.identification(self.context.stage_name)}",
            allow_all_outbound=True,
        )
        security_group.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(22), "SSH Access")
        security_group.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(80), "HTTPS Access")
        security_group.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(443), "HTTPS Access")
        bastion_security_group = ec2.SecurityGroup(
            self,
            f"{self.identification(self.context.stage_name)}-bastion-security-group",
            security_group_name=f"{self.identification(self.context.stage_name)}-bastion-security-group-firewall",
            vpc=vpc,
            description=f"bastion security group for {self.identification(self.context.stage_name)}",
            allow_all_outbound=True,
        )
        bastion_security_group.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(22), "SSH Access")
        return security_group, bastion_security_group

    def get_ec2_block_devices(self):
        block_device_volume = ec2.BlockDeviceVolume.ebs(self.context.volume_size, delete_on_termination=True)

        return [
            ec2.BlockDevice(
                device_name="/dev/sda1",  # IMPORTANT: this is the root device and may depend on the AMI image used.
                volume=block_device_volume,
            )
        ]

    @abstractmethod
    def create_role(self):
        pass

    @abstractmethod
    def transform_user_data(self, i: int):
        pass

    @staticmethod
    @abstractmethod
    def subnet_selection(i: int):
        pass
