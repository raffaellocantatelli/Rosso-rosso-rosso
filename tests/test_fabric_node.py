import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from r3_peer.backup import InMemoryBackupStore
from r3_peer.channels import InMemoryChannelRegistry
from r3_peer.fabric_node import FabricNode
from r3_peer.factory import build_fabric_node, build_registry_store
from r3_peer.in_memory import InMemoryNodeRegistry
from r3_peer.provref import OpaqueProvrefError


class FabricNodeTests(unittest.TestCase):
    def setUp(self) -> None:
        os.environ.pop("PROVIDER_ACCOUNT_REF", None)
        os.environ.pop("NODE_REGISTRY_DSN", None)
        self.store = InMemoryNodeRegistry()
        self.backup = InMemoryBackupStore()
        self.channels = InMemoryChannelRegistry()
        self.node = FabricNode(
            "n1",
            self.store,
            backup_store=self.backup,
            channel_registry=self.channels,
            provider_account_ref="provref:local-test-001",
        )

    def test_register_rotate_revoke_and_backup(self) -> None:
        self.node.register_key("k1", "pub-1")
        active = self.node.get_active()
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["key_id"], "k1")

        rotated = self.node.rotate_key("k1", "k2", "pub-2")
        self.assertEqual(rotated["old"]["status"], "revoked")
        self.assertEqual(rotated["new"]["key_id"], "k2")
        self.assertEqual([k["key_id"] for k in self.node.get_active()], ["k2"])

        self.node.revoke_key("k2")
        self.assertEqual(self.node.get_active(), [])
        self.assertEqual(len(self.backup.snapshots), 3)

    def test_observed_vs_canonical(self) -> None:
        seen = self.node.observe_channel("ch-a", "head-obs")
        self.assertFalse(seen["aligned"])
        self.assertEqual(seen["observed_head"], "head-obs")
        self.assertIsNone(seen["canonical_head"])

        committed = self.node.commit_canonical_head("ch-a", "head-obs")
        self.assertTrue(committed["aligned"])
        self.assertEqual(self.node.channel_heads("ch-a")["canonical_head"], "head-obs")

    def test_raw_account_rejected(self) -> None:
        with self.assertRaises(OpaqueProvrefError):
            FabricNode("n1", self.store, provider_account_ref="user@provider")

    def test_factory_does_not_need_dsn(self) -> None:
        node = build_fabric_node("n-factory")
        self.assertIsInstance(node.registry, InMemoryNodeRegistry)
        store = build_registry_store()
        self.assertIsInstance(store, InMemoryNodeRegistry)

    def test_from_env_delegates_and_does_not_import_pg(self) -> None:
        node = FabricNode.from_env("n-env")
        self.assertEqual(node.node_id, "n-env")
        src = open(
            os.path.join(os.path.dirname(__file__), "..", "r3_peer", "fabric_node.py"),
            encoding="utf-8",
        ).read()
        self.assertNotIn("PostgreSQLNodeRegistry(", src)
        self.assertNotIn("InMemoryNodeRegistry()", src)


if __name__ == "__main__":
    unittest.main()
