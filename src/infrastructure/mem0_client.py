"""
---------------------------------
src/infrastructure/mem0_client.py
---------------------------------

# Simple encapsulation of requests to mem0 servers, 
# implemented as Mem0Client class.

# WARN: The new additions to the vector database are close to real-time, 
# but not immediate. Therefore, a certain response time must be allowed for each test. 
# If the response time exceeds 7.5 seconds, the access is considered a failure.

- Hosted / self-hosted REST ->  MemoryClient(host, api_key)
- Local open-source mode    ->  Memory()
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Optional, Any, List, Union
from dotenv import load_dotenv
import os
import uuid
import time

from mem0 import Memory, MemoryClient

load_dotenv()


### -------------------------------------------------------
### Exception class definition
### -------------------------------------------------------

class Mem0ConnectionError(RuntimeError):
    """
    Failed to pass health check during initialization.
    Generally, the user enters an error URL or API.
    """

class Mem0APIError(RuntimeError):
    """
    Thrown when write/check fails at runtime
    Further analysis is required based on the error code.
    """


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
    
    Parameters
    ----------
    api_key : str | None
        Required for hosted mode; None is optional for self-built mode.
    use_hosted : bool
        True: Use platform-hosted Graph Memory;
        False: Use open source Memory + self-built graph storage (Neo4j).
    graph_config : dict
        Self-built graph storage parameters; activate only when use_hosted=False
        dict(    
            provider="neo4j",
            url="bolt://localhost:7687",
            username="neo4j",
            password="password",
        )
    vector_config : dict, optional
        Custom vector storage parameters.
        Usually keep None, use mem0 default HybridStore
    """
    
    host: Optional[str] = "https://api.mem0.ai"
    api_key: Optional[str] = None
    
    _client: Any = field(init=False, repr=False)
    
    # Post-initialization transaction hook function(Life Cycle)
    def __post_init__(self) -> None:
        host = (self.host or "").strip()
        self.api_key = self.api_key or os.getenv("MEM0_API_KEY")
        
        try:
            if host:
                if not self.api_key:
                    raise ValueError("In host mode, you must provide api_key or set MEM0_API_KEY.")
                self._client = MemoryClient(host=host, 
                                            api_key=self.api_key)
            else:
                
                # TODO 尚未完成本地直接调用部分. 考虑到实际情况, 可能会放弃此方案.
                
                self._client = Memory()
        
        except Exception as exc: # noqa: BLE001
            raise Mem0ConnectionError(f"Mem0 Initialization failed: {exc}") from exc
        
        self._health_check()
    
    # Public: Add memory to database
    def add_memory(
        self,
        messages: Union[str, List[Dict[str, str]]],
        *,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: str = "Undefined",
        infer: Optional[bool] = False
    ) -> Dict[str, Any]:
        """
        Write a memory (automatic drop image & vector)
        
        Parameters
        ----------
        messages : list | str
        metadata: dict, optional
        user_id: str
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
            raise Mem0APIError(f"add_memory Failed: {exc}") from exc

    # Public: Search memory in database
    def search(
        self,
        query: str,
        *,
        user_id: str = "Undefined",
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Hybrid Search
        
        Parameters
        ----------
        query : str
        metadata: dict
        user_id: str
        """
        try:
            return self._client.search(
                query,
                user_id=user_id,
                limit=limit
            )
        except Exception as exc: # noqa: BLE001
            raise Mem0APIError(f"search failed: {exc}") from exc

    # Public: Delete memory by id
    def delete_memory(self, memory_id: str) -> Dict[str, Any]:
        try:
            return self._client.delete(memory_id)
        except Exception as exc:  # noqa: BLE001
            raise Mem0APIError(f"delete failed: {exc}") from exc

    def delete_user_memories(self, user_id: str) -> None:
        """Delete all memories for a user (used for tests cleanup)"""
        try:
            self._client.delete_all(user_id=user_id)
        except Exception as exc:  # noqa: BLE001
            raise Mem0APIError(f"delete_user_memories failed: {exc}") from exc
        
    # Health-Check
    def _health_check(self) -> None:
        """
        Write & immediately retrieve a dummy message to verify pipeline.
        """
        token = f"__health_{uuid.uuid4()}__"
        mem_id: str | None = None
        try:
            rsp = self._client.add(
                [
                    {
                        "role": "user",
                        "content": token,
                    }
                ],
                infer=False,
                user_id="__health_check__",
                output_format="v1.1",
            )
            if isinstance(rsp, dict):
                mem_id = rsp.get("id")
            # If the response time exceeds 7.5 seconds, the access is considered a failure.
            for attempt in range(1, 6):
                hits = self._client.search(
                    token,
                    user_id = "__health_check__",
                    limit = 1
                )
                if hits:
                    return
                sleep_for = 0.5 * attempt
                time.sleep(sleep_for)
            raise Mem0ConnectionError("Mem0ConnectionError: When initialized. Unable to retrieve the data")
        except Exception as exc: # noqa: BLE001
            raise Mem0ConnectionError(f"Mem0ConnectionError: When initialized. error: {exc}") from exc
        finally:
            try:
                if mem_id:
                    self._client.delete(mem_id)
                self._client.delete_all(user_id="__health_check__")
            except Exception:
                pass
        

### -------------------------------------------------------
### USE FOR TEST
### -------------------------------------------------------

if __name__ == "__main__":
    import os
    
    api_key = os.getenv("MEM0_API_KEY")
    def test_add_and_search():
        client = Mem0Client()  # 默认托管平台
        client.add_memory("Graph-vector demo", user_id="ci")
        out = client.search("graph-vector", user_id="ci", limit=1)
        print(out[0]["memory"])
    
    test_add_and_search()