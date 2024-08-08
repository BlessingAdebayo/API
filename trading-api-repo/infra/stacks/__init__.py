from aws_cdk import core


class Stack(core.Stack):
    @property
    def name(self):
        raise NotImplementedError("implement me in child class")

    def identification(self, stage_name: str) -> str:
        return f"{self.name}-{stage_name}"
