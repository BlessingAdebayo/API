from dataclasses import dataclass


@dataclass
class RSEContext:
    stage_name: str
    project_name: str
    vpc_subnet_cidr: str
    instance_type: str
    dns: str
    cert_arn: str
    access_key_name: str
    nr_instances: int
    volume_size: int
    image_tag: str
    subnetwork_base_algonodes: int
