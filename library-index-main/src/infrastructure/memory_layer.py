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
        {
                "role": "user",
                "content": MEM0_PING_CONTENT
        }
]


### -------------------------------------------------------
### Mem0 API Wrapper
### -------------------------------------------------------

# Helper
def _wrap_messages(msg: Union[str, List[Dict[str, str]]]) -> List[Dict[str, str]]:
    """
    EPackages the input into a message list in the format [{'role': 'user', 'content': ...}]

params
------
msg: str or list. A string is treated as a user message; a dictionary is used directly.

return
------
A standardized message dictionary list, used to submit to the MemoryClient
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
        """
Initializes the Mem0Client client, choosing whether to call the hosted service or the local instance based on whether the host and api_key are configured.

params
------
None

return
------
None (throws an exception if the connection fails)
"""
        host = self.host if self.host else "https://api.mem0.ai"
        
        try:
            if host:
                if not self.api_key:
                    raise ValueError("In host mode, you must set MEM0_API_KEY.")
                self._client = MemoryClient(host=host, api_key=self.api_key)
            else:
                # TODO 尚未完成本地直接调用部分. 考虑到实际情况, 可能会放弃此方案.
                self._client = Memory()
        
        except Exception as exc: # noqa: BLE001
            raise Mem0InitConnectError(f"Mem0 Initialization failed: {exc}") from exc
        self._health_check()

    
    def add_memory(
        self,
        messages: Union[str, List[Dict[str, str]]],
        *,
        metadata: Dict[str, Any],
        user_id: str = "Undefined",
        infer: Optional[bool] = False
    ) -> Dict[str, Any]:
        """
Adds a memory to Mem0 (automatically drops the graph and vector).

params
------
messages: Message content, which can be a string or a formatted dictionary list
metadata: Metadata dictionary recording the memory context
user_id: User ID (defaults to "Undefined")
infer: Whether to perform model inference (defaults to False)

return
------
Response dictionary after successful addition, containing information such as the generated memory ID.
        """
        try:
            return self._client.add(
                _wrap_messages(messages), 
                metadata=metadata or {},
                output_format="v1.1",
                infer=infer,
                user_id=user_id
            )
        except Exception as exc: # noqa: BLE001
            raise Mem0ConnectError(f"add_memory Failed: {exc}") from exc


    def search_metadata(self, metadata: str) -> List[Dict[str, Any]]:
        """
Searches based on the specified id field in the metadata.

params
------
metadata: The unique identifier field value in the metadata used for the search.

return
------
A list of matching records found (or an empty list if no matches are found).
        """
        return self._client.search(
            query="*",
            version="v2",
            filters={
                "AND": [
                    {
                        "metadata": {
                            "eq": {
                                "id": f"{metadata}"
                            }
                        }
                    }
                ]
            }
        )


    def search(
        self,
        query: str,
        *,
        user_id: str = "Undefined",
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
Performs a hybrid search on memory content.

params
------
query: Search query (string)
user_id: User ID (default "Undefined")
limit: Number of results to return (default 10)

return
------
A list of dictionaries containing matching search results
        """
        try:
            return self._client.search(
                query,
                user_id=user_id,
                limit=limit
            )
        except Exception as exc: # noqa: BLE001
            raise Mem0ConnectError(f"search failed: {exc}") from exc

    def delete_memory(self, memory_id: str) -> Dict[str, Any]:
        """
Deletes the memory with the specified ID.

params
------
memory_id: The ID of the memory to be deleted.

return
------
The dictionary containing the response from the delete operation.
"""
        try:
            return self._client.delete(memory_id)
        except Exception as exc:  # noqa: BLE001
            raise Mem0ConnectError(f"delete failed: {exc}") from exc

    def delete_user_memories(self, user_id: str) -> None:
        """
Delete all memoization records for the specified user

params
------
user_id: The user ID for which all memoizations are to be deleted

return
------
None (operation successful or an exception is thrown)
"""
        try:
            self._client.delete_all(user_id=user_id)
        except Exception as exc:  # noqa: BLE001
            raise Mem0ConnectError(f"delete_user_memories failed: {exc}") from exc
        
    def _health_check(self) -> None:
        """
Writes and retrieves a dummy message to verify API pipeline connectivity.

params
------
None

return
------
None (throws an exception if the connection fails or times out)        """
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
                    query=MEM0_PING_CONTENT,
                    user_id = "__health_check__",
                    limit = 1
                )
                if hits:
                    return
                sleep_for = 0.5 * attempt
                time.sleep(sleep_for)
            raise Mem0ConnectError("Mem0ConnectionError: When initialized. Unable to retrieve the data.")
        except Exception as exc: # noqa: BLE001
            raise Mem0ConnectError(f"Mem0ConnectionError: When initialized. error: {exc}.") from exc
        finally:
            try:
                if mem_id:
                    self.delete_memory(mem_id)
                self.delete_user_memories(user_id="__health_check__")
            except Exception:
                raise Mem0ConnectError("Mem0ConnectionError: When initialized. Unable to delete written memory.")
        

if __name__ == "__main__":
    import os
    
    api_key = os.getenv("MEM0_API_KEY")
    
    def test_add_and_search():
        client = Mem0Client()  # 默认托管平台
        client.add_memory("Graph-vector demo", user_id="__ci__", metadata={"Name": "Flower Dance",})
        out = client.search("graph-vector", user_id="__ci__", limit=1)
        client.delete_user_memories(user_id="__ci__")
        print(out)
    
    test_add_and_search()
