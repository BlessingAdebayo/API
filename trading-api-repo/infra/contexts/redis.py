from dataclasses import dataclass


@dataclass
class RedisContext:
    stage_name: str
    instance_type: str
