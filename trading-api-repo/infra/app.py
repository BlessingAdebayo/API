#!/usr/bin/env python3

import os
import subprocess
from typing import List, Dict

from aws_cdk import core

from contexts.mongodb import MongoContext
from contexts.redis import RedisContext
from contexts.subnet import SubnetContext
from contexts.trading_api import TradingApiContext
from contexts.rse import RSEContext
from stacks.postgres import PostgresStack
from stacks.rse import RSEStack
from stacks.mongodb import MongoStack
from stacks.redis import RedisStack
from stacks.trading_api import TradingAPIStack
from stacks.vpc import VPCStack


def add_stacks_for_trading_api_environment(
    app,
    context: TradingApiContext,
    mo_context: MongoContext,
    r_context: RedisContext,
    subnet_context: List[SubnetContext],
    environment,
):
    tags = {"stage": context.stage_name}
    vpc = VPCStack(app, context=context, env=environment, tags=tags, subnet_context=subnet_context)
    redis = RedisStack(app, vpc=vpc.vpc, redis_context=r_context, env=environment, tags=tags)
    mongo = MongoStack(app, vpc=vpc.vpc, mongo_context=mo_context, env=environment, tags=tags)
    TradingAPIStack(app, context=context, vpc=vpc.vpc, redis=redis, mongo=mongo, env=environment, tags=tags)


def add_stacks_for_rse_environment(app, context: RSEContext, subnet_context: List[SubnetContext], environment):
    tags = {
        "stage": context.stage_name,
    }
    vpc = VPCStack(app, context=context, env=environment, tags=tags, prefix="rse-", subnet_context=subnet_context)
    postgres = PostgresStack(app, stage_name=context.stage_name, vpc=vpc.vpc, env=environment, tags=tags)
    RSEStack(app, vpc=vpc.vpc, context=context, postgres=postgres, env=environment, tags=tags)


def get_context(context: dict, tag: str):
    return TradingApiContext(
        stage_name=context["stage_name"],
        project_name=context["project_name"],
        vpc_subnet_cidr=context["vpc_subnet_cidr"],
        instance_type=context["ec2_type"],
        dns=context["dns_name"],
        cert_arn=context["certificate_arn"],
        access_key_name=context["access_key_name"],
        nr_instances=context["nr_instances"],
        volume_size=context["volume_size"],
        image_tag=tag,
    )


def get_rse_context(context: dict, tag: str):
    return RSEContext(
        stage_name=context["stage_name"],
        project_name=context["project_name"],
        vpc_subnet_cidr=context["vpc_subnet_cidr"],
        instance_type=context["ec2_type"],
        dns=context["dns_name"],
        cert_arn=context["certificate_arn"],
        access_key_name=context["access_key_name"],
        nr_instances=context["nr_instances"],
        volume_size=context["volume_size"],
        image_tag=tag,
        subnetwork_base_algonodes=context["subnetwork_base_algonodes"],
    )


def get_subnet_context(context: Dict[str, List]):
    return [SubnetContext(**con) for con in context["subnets"]]


def get_mongo_context(context: dict):
    return MongoContext(stage_name=context["stage_name"], **(context["mongo"]))


def get_redis_context(context: dict):
    return RedisContext(stage_name=context["stage_name"], **(context["redis"]))


DEFAULT_REGION = "eu-west-1"

_app = core.App()

_environment = core.Environment(
    account=os.environ.get("CDK_DEPLOY_ACCOUNT", os.environ["CDK_DEFAULT_ACCOUNT"]),
    region=os.environ.get("CDK_DEPLOY_REGION", os.environ.get("CDK_DEFAULT_REGION", DEFAULT_REGION)),
)

completed_command = subprocess.run(
    ["git", "rev-parse", "HEAD"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
)
image_tag = completed_command.stdout.strip()

stages = ["staging", "development", "production"]

for stage in stages:
    trading_api_contexts = _app.node.try_get_context("trading_api")
    stage_context: TradingApiContext = get_context(trading_api_contexts[stage], tag=image_tag)
    mongo_context = get_mongo_context(trading_api_contexts[stage])
    redis_context = get_redis_context(trading_api_contexts[stage])
    trading_api_subnet_context = get_subnet_context(trading_api_contexts[stage])
    add_stacks_for_trading_api_environment(
        _app, stage_context, mongo_context, redis_context, trading_api_subnet_context, environment=_environment
    )

    rse_contexts = _app.node.try_get_context("rse")
    rse_context = get_rse_context(rse_contexts[stage], tag=image_tag)
    rse_subnet_context = get_subnet_context(rse_contexts[stage])
    add_stacks_for_rse_environment(_app, rse_context, rse_subnet_context, environment=_environment)

_app.synth()
