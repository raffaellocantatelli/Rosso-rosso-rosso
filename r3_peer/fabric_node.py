"""
CAP-R3-004: FabricNode dipende da NodeRegistryStore.
Non istanzia PostgreSQLNodeRegistry né InMemoryNodeRegistry.

R3-PEER/1.1c: ChannelRegistry, observed vs canonical head, provref opaco.
"""

from __future__ import annotations

from typing import Any, Optional

from .provref import provider_account_ref_from_env
from .store import BackupStore, ChannelRegistry, NodeRegistryStore


class FabricNode:
    def __init__(
        self,
        node_id: str,
        registry_store: NodeRegistryStore,
        backup_store: Optional[BackupStore] = None,
        channel_registry: Optional[ChannelRegistry] = None,
        *,
        require_provref: bool = False,
        provider_account_ref: Optional[str] = None,
    ) -> None:
        if not node_id:
            raise ValueError("node_id obbligatorio")
        if registry_store is None:
            raise ValueError("registry_store obbligatorio (CAP-R3-004)")
        self.node_id = node_id
        self.registry: NodeRegistryStore = registry_store
        self.backup_store = backup_store
        self.channel_registry = channel_registry
        if provider_account_ref is not None:
            from .provref import parse_provref

            self.provider_account_ref = parse_provref(
                provider_account_ref, required=require_provref
            )
        else:
            self.provider_account_ref = provider_account_ref_from_env(
                required=require_provref
            )

    def _snapshot(self, record: Any) -> None:
        if self.backup_store is None or record is None:
            return
        payload = record["new"] if isinstance(record, dict) and "new" in record else record
        self.backup_store.snapshot(self.node_id, payload if isinstance(payload, dict) else {"value": payload})

    def register_key(self, key_id: str, public_key: str) -> dict[str, Any]:
        res = self.registry.register(self.node_id, key_id, public_key)
        self._snapshot(res)
        return res

    def rotate_key(self, old_key_id: str, new_key_id: str, new_public_key: str) -> dict[str, Any]:
        res = self.registry.rotate(self.node_id, old_key_id, new_key_id, new_public_key)
        self._snapshot(res)
        return res

    def revoke_key(self, key_id: str) -> dict[str, Any]:
        res = self.registry.revoke(self.node_id, key_id)
        self._snapshot(res)
        return res

    def get_active(self) -> list[dict[str, Any]]:
        return self.registry.get_active(self.node_id)

    def observe_channel(self, channel_id: str, observed_head: str) -> dict[str, Any]:
        if self.channel_registry is None:
            raise RuntimeError("channel_registry non iniettato")
        return self.channel_registry.observe(channel_id, observed_head)

    def commit_canonical_head(self, channel_id: str, canonical_head: str) -> dict[str, Any]:
        if self.channel_registry is None:
            raise RuntimeError("channel_registry non iniettato")
        return self.channel_registry.set_canonical(channel_id, canonical_head)

    def channel_heads(self, channel_id: str) -> dict[str, Any]:
        if self.channel_registry is None:
            raise RuntimeError("channel_registry non iniettato")
        return self.channel_registry.get_heads(channel_id)

    @staticmethod
    def from_env(node_id: str) -> "FabricNode":
        """Compat: delega alla factory. Non istanzia PG/InMemory qui."""
        from .factory import build_fabric_node

        return build_fabric_node(node_id)
