"""CAP-R3-004: contratti store. Nessuna implementazione concreta qui."""

from __future__ import annotations

from typing import Any, Mapping, Protocol, runtime_checkable


@runtime_checkable
class NodeRegistryStore(Protocol):
    def register(self, node_id: str, key_id: str, public_key: str) -> dict[str, Any]: ...

    def rotate(
        self,
        node_id: str,
        old_key_id: str,
        new_key_id: str,
        new_public_key: str,
    ) -> dict[str, Any]: ...

    def revoke(self, node_id: str, key_id: str) -> dict[str, Any]: ...

    def get_active(self, node_id: str) -> list[dict[str, Any]: ...


@runtime_checkable
class BackupStore(Protocol):
    def snapshot(self, node_id: str, record: Mapping[str, Any]) -> None: ...


@runtime_checkable
class ChannelRegistry(Protocol):
    """R3-PEER/1.1c: observed head ≠ canonical head finché non allineati."""

    def observe(self, channel_id: str, observed_head: str) -> dict[str, Any]: ...

    def set_canonical(self, channel_id: str, canonical_head: str) -> dict[str, Any]: ...

    def get_heads(self, channel_id: str) -> dict[str, Any]: ...
