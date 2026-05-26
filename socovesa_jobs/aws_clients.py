from __future__ import annotations

from dataclasses import dataclass

import boto3

from .config import Settings, boto_config, settings


@dataclass(frozen=True)
class AwsClients:
    s3: object
    bedrock: object
    bedrock_agent_runtime: object
    bedrock_agent: object


def create_aws_clients(cfg: Settings = settings) -> AwsClients:
    session = boto3.Session(region_name=cfg.aws_region)
    config = boto_config()
    return AwsClients(
        s3=session.client("s3", config=config),
        bedrock=session.client("bedrock-runtime", config=config),
        bedrock_agent_runtime=session.client("bedrock-agent-runtime", config=config),
        bedrock_agent=session.client("bedrock-agent", config=config),
    )
