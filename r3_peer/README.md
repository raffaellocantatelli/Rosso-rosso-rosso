# r3_peer / FabricNode

Modulo CAP-R3-004 + R3-PEER/1.1c. Branch `grok/r3-peer-fabric-node`. Railway non toccato. Checkpoint 0615 non toccato.

## Contratto

- `FabricNode` riceve un `NodeRegistryStore`. Non istanzia PG o InMemory.
- La scelta dello store sta in `factory.build_registry_store()` (`NODE_REGISTRY_DSN` → Postgres, altrimenti InMemory).
- `from_env()` è solo un wrapper sulla factory.
- Provref: solo `provref:<opaque-id>`. Account raw → errore.
- Channel: `observe_channel` vs `commit_canonical_head`. `aligned` solo se i due head coincidono.
- Backup snapshot su register / rotate / revoke.

## Uso

```python
from r3_peer import FabricNode, build_fabric_node
from r3_peer.in_memory import InMemoryNodeRegistry

node = FabricNode("n1", InMemoryNodeRegistry(), provider_account_ref="provref:local-001")
node.register_key("k1", "ssh-ed25519 AAAA...")
node.observe_channel("peer-mcp", "obs-hash")
node.commit_canonical_head("peer-mcp", "obs-hash")

# composition root
live = build_fabric_node("n1")  # DSN da env se presente
```

Env:

- `NODE_REGISTRY_DSN` — opzionale
- `PROVIDER_ACCOUNT_REF` — `provref:...`
- `R3_NODE_ID` — usato da `build_fabric_node()` se manca l'argomento

## Test

```bash
python -m unittest tests.test_fabric_node
```
