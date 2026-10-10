"""Composition root CAP-R3-004: qui si scelgono PG / InMemory, non in FabricNode."""

from __future__ import annotations

import os
from typing import Optional

from .backup import InMemoryBackupStore
from .channels import InMemoryChannelRegistry
from .fabric_node import FabricNode
from .in_memory import InMemoryNodeRegistry
from .store import BackupStore, ChannelRegistry, NodeRegistryStore

ENV_NODE_REGISTRY_DSN = "NODE_REGISTRY_DSN"
ENV_NODE_ID = "R3_NODE_ID"


def build_registry_store(dsn: Optional[str] = None) -> NodeRegistryStore:
    resolved = dsn if dsn is not None else os.getenv(ENV_NODE_REGISTRY_DSN)
    if resolved:
        from .postgres import PostgreSQLNodeRegistry

        return PostgreSQLNodeRegistry(dsn=resolved)
    return InMemoryNodeRegistry()


def build_fabric_node(
    node_id: Optional[str] = None,
    *,
    registry_store: Optional[NodeRegistryStore] = None,
    backup_store: Optional[BackupStore] = None,
    channel_registry: Optional[ChannelRegistry] = None,
    require_provref: bool = False,
) -> FabricNode:
    nid = node_id or os.getenv(ENV_NODE_ID)
    if not nid:
        raise ValueError("node_id obbligatorio (argomento o R3_NODE_ID)")
    return FabricNode(
        node_id=nid,
        registry_store=registry_store or build_registry_store(),
        backup_store=backup_store if backup_store is not None else InMemoryBackupStore(),
        channel_registry=channel_registry if channel_registry is not None else InMemoryChannelRegistry(),
        require_provref=require_provref,
    )
