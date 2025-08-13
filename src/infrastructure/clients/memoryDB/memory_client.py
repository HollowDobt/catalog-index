"""
# src/infrastructure/clients/memoryDB/memory_client.py

Memory layer component based on mem0

基于 mem0 的记忆层组件
"""


from __future__ import annotations

import time
import logging

from typing import Dict, Optional, Any, List, Union
from mem0 import MemoryClient

from config import CONFIG


logger = logging.getLogger(__name__)

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
    else:
        logger.warning(f"Messages must be string or list. Now return []")
        return []


class Mem0Client:
    """
    High-level wrapper for mem0 SDK.
    """
    
    def __init__(self) -> None:
        host: Optional[str] = CONFIG["MEM0_BASE_URL"]
        api_key: Optional[str] = CONFIG["MEM0_API_KEY"]
        self._client = MemoryClient(host=host, api_key=api_key)
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

        logger.info(f"Add memory: {metadata['id']}")
        return self._client.add(
                _wrap_messages(messages),
                metadata=metadata or {},
                output_format="v1.1",
                infer=infer,
                user_id=user_id,
        )
    
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
        logger.info(f"Search memory: {metadata}")
        return self._client.search(
            query="*",
            version="v2",
            filters={"AND": [{"metadata": {"eq": {"id": f"{metadata}"}}}]},
        )
        
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
        logger.info(f"Delete memory. Memory ID: {memory_id}")
        return self._client.delete(memory_id=memory_id)

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
        logger.info(f"Delete user's memory. User ID: {user_id}")
        self._client.delete_all(user_id=user_id)
        
    def _health_check(self) -> None:
        """
        Write & immediately retrieve a dummy message to verify pipeline.
        """
        mem_id: Optional[str] = None
        try:
            response = self._client.add(
                CONFIG["MEM0_PING_MESSAGES"],
                infer=False,
                user_id="__health_check__",
                output_format="v1.1",
            )
            if isinstance(response, dict):
                mem_id = response.get("id")
            # If the response time exceeds 7.5 seconds, the access is considered a failure.
            for attempt in range(1, 6):
                hits = self._client.search(
                    query=CONFIG["MEM0_PING_CONTENT"], user_id="__health_check__", limit=1
                )
                if hits:
                    logger.info("Retrieve data success")
                    return
                logger.warning(f"Find failed. Try again")
                sleep_for = 0.5 * attempt
                time.sleep(sleep_for)
            logger.error(f"Find failed. Unable retrieve the data.")
        except Exception as exc:
            logger.error(f"Health check failed. Details: {exc}")
            raise RuntimeError(
                f"Mem0ConnectionError: When initialized. error: {exc}."
            )
        finally:
            try:
                if mem_id:
                    self.delete_memory(mem_id)
                self.delete_user_memories(user_id="__health_check__")
                logger.info(f"Delete test success")
            except Exception as exc:
                logger.warning(f"Unable to delete memory. Details: {exc}")