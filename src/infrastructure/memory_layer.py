"""
====================================
|src/infrastructure/memory_layer.py|
====================================

# Simple encapsulation of requests to mem0 servers,
"""

from __future__ import annotations

import os
import uuid
import time
from dotenv import load_dotenv

from dataclasses import dataclass, field
from typing import Dict, Optional, Any, List, Union
from pathlib import Path
from mem0 import Memory, MemoryClient

DOT_ENV_PATH_PUBLIC = Path(__file__).parent.parent.parent / ".public.env"
DOT_ENV_PATH_PRIVATE = Path(__file__).parent.parent.parent / ".private.env"
load_dotenv(DOT_ENV_PATH_PUBLIC)
load_dotenv(DOT_ENV_PATH_PRIVATE)


class Mem0InitConnectError(RuntimeError):
    """
    Failed to get 200 code when initialization.
    """


class Mem0ConnectError(RuntimeError):
    """
    Failed to get 200 code.
    """


MEM0_PING_CONTENT = f"__health_{uuid.uuid4()}__"
MEM0_PING_MESSAGES: List[Dict[str, str]] = [
    {"role": "user", "content": MEM0_PING_CONTENT}
]


### -------------------------------------------------------
### Mem0 API Wrapper
### -------------------------------------------------------


# Helper
def _wrap_messages(msg: Union[str, List[Dict[str, str]]]) -> List[Dict[str, str]]:
    """
    Ensure we always pass a 'list[{"role", "content"}]' to 'client.add()'

    * If the caller gives a plain string -> treat it as a 'user' message.
    * If it's already a list -> assume caller formatted it correctly.
    """
    if isinstance(msg, str):
        return [{"role": "user", "content": msg}]
    if isinstance(msg, list) and all(isinstance(m, dict) for m in msg):
        return msg
    raise ValueError("messages must be a str or list[dict{'role','content'}]")


@dataclass
class Mem0Client:
    """
    High-level wrapper for mem0 SDK.

    Default host = https://api.mem0.ai
    """

    host: str | None = os.getenv("MEM0_BASE_URL")
    api_key: str | None = os.getenv("MEM0_API_KEY")

    _client: Any = field(init=False, repr=False)

    def __post_init__(self) -> None:

        host = self.host if self.host else "https://api.mem0.ai"

        try:
            if host:
                if not self.api_key:
                    raise ValueError("In host mode, you must set MEM0_API_KEY.")
                self._client = MemoryClient(host=host, api_key=self.api_key)
            else:
                # TODO 尚未完成本地直接调用部分. 考虑到实际情况, 可能会放弃此方案.
                self._client = Memory()

        except Exception as exc:  # noqa: BLE001
            raise Mem0InitConnectError(f"Mem0 Initialization failed: {exc}") from exc
        self._health_check()

    def add_memory(
        self,
        messages: Union[str, List[Dict[str, str]]],
        *,
        metadata: Dict[str, Any],
        user_id: str = "Undefined",
        infer: Optional[bool] = False,
    ) -> Dict[str, Any]:
        """
        Write a memory (automatic drop graph & vector).

        params
        ------
        messages: message content to store
        metadata: metadata associated with the memory
        user_id: identifier for the user
        infer: whether to perform inference during storage

        return
        ------
        Dictionary containing the server response
        """
        try:
            return self._client.add(
                _wrap_messages(messages),
                metadata=metadata or {},
                output_format="v1.1",
                infer=infer,
                user_id=user_id,
            )
        except Exception as exc:  # noqa: BLE001
            raise Mem0ConnectError(f"add_memory Failed: {exc}") from exc

    def search_metadata(self, metadata: str) -> List[Dict[str, Any]]:
        """
        Search for memories by unique identifier.

        params
        ------
        metadata: unique identification code

        return
        ------
        List of matching memory records
        """
        return self._client.search(
            query="*",
            version="v2",
            filters={"AND": [{"metadata": {"eq": {"id": f"{metadata}"}}}]},
        )

    def search(
        self,
        query: str,
        *,
        user_id: str = "Undefined",
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Perform a hybrid search.

        params
        ------
        query: search text
        user_id: identifier for the user
        limit: maximum number of results

        return
        ------
        List of memory records matching the query
        """
        try:
            return self._client.search(query, user_id=user_id, limit=limit)
        except Exception as exc:  # noqa: BLE001
            raise Mem0ConnectError(f"search failed: {exc}") from exc

    def delete_memory(self, memory_id: str) -> Dict[str, Any]:
        """
        Delete a memory by its ID.

        params
        ------
        memory_id: identifier of the memory to remove

        return
        ------
        Server response for the delete operation
        """
        try:
            return self._client.delete(memory_id)
        except Exception as exc:  # noqa: BLE001
            raise Mem0ConnectError(f"delete failed: {exc}") from exc

    def delete_user_memories(self, user_id: str) -> None:
        """
        Delete all memories for a user.

        params
        ------
        user_id: identifier of the user

        return
        ------
        None
        """
        try:
            self._client.delete_all(user_id=user_id)
        except Exception as exc:  # noqa: BLE001
            raise Mem0ConnectError(f"delete_user_memories failed: {exc}") from exc

    def _health_check(self) -> None:
        """
        Write & immediately retrieve a dummy message to verify pipeline.
        """
        mem_id: str | None = None
        try:
            response = self._client.add(
                MEM0_PING_MESSAGES,
                infer=False,
                user_id="__health_check__",
                output_format="v1.1",
            )
            if isinstance(response, dict):
                mem_id = response.get("id")
            # If the response time exceeds 7.5 seconds, the access is considered a failure.
            for attempt in range(1, 6):
                hits = self._client.search(
                    query=MEM0_PING_CONTENT, user_id="__health_check__", limit=1
                )
                if hits:
                    return
                sleep_for = 0.5 * attempt
                time.sleep(sleep_for)
            raise Mem0ConnectError(
                "Mem0ConnectionError: When initialized. Unable to retrieve the data."
            )
        except Exception as exc:  # noqa: BLE001
            raise Mem0ConnectError(
                f"Mem0ConnectionError: When initialized. error: {exc}."
            ) from exc
        finally:
            try:
                if mem_id:
                    self.delete_memory(mem_id)
                self.delete_user_memories(user_id="__health_check__")
            except Exception:
                raise Mem0ConnectError(
                    "Mem0ConnectionError: When initialized. Unable to delete written memory."
                )


if __name__ == "__main__":
    import os

    api_key = os.getenv("MEM0_API_KEY")

    def test_add_and_search():
        client = Mem0Client()  # 默认托管平台
        client.add_memory(
            "Graph-vector demo",
            user_id="__ci__",
            metadata={
                "Name": "Flower Dance",
            },
        )
        out = client.search("graph-vector", user_id="__ci__", limit=1)
        client.delete_user_memories(user_id="__ci__")
        print(out)

    test_add_and_search()
