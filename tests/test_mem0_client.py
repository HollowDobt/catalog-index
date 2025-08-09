import os
import pytest
import sys

sys.path.extend(["src", "src/infrastructure"])
from infrastructure.mem0_client import Mem0Client


@pytest.mark.skipif(not os.getenv("MEM0_API_KEY"), reason="MEM0_API_KEY not set")
def test_add_and_delete():
    client = Mem0Client()
    res = client.add_memory("test entry", user_id="ci-test")
    mid = res.get("id")
    assert mid
    hits = client.search("test entry", user_id="ci-test", limit=1)
    assert hits and hits[0]["id"] == mid
    client.delete_memory(mid)
    client.delete_user_memories("ci-test")
