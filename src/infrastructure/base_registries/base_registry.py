"""
# src/infrastructure/registries/base_registry.py

Registrar component, public base class template

注册器组件, 公共基类模版
"""


from __future__ import annotations
from typing import Any, Dict, Type, TypeVar, Generic


T = TypeVar("T", bound="LIStandard")


class LIStandard(Generic[T]):
    """
    Minimum implementing a name based registry and factory
    """
    
    _registry: Dict[str, Type[T]]
    
    def __init_subclass__(cls, **kwargs: Any) -> None: # pragma: no cover
        super().__init_subclass__(**kwargs)
        # Ensure every subclass gets its own independent registry
        cls._registry = {}
    
    @classmethod
    def register(cls: Type[T], name: str):
        """
        Register a subclass under ``name``.
        """
        
        def decorator(subcls: Type[T]) -> Type[T]:
            if name in cls._registry:
                raise KeyError(
                    f"{cls.__name__} provider '{name}' cannot be registered again."
                )
            cls._registry[name] = subcls
            return subcls
        
        return decorator
    
    @classmethod
    def create(cls: Type[T], provider_name: str, **kwargs: Any) -> T:
        """
        Instantiate a registered subclass by ``provider_name``.
        """
        
        subcls = cls._registry.get(provider_name)
        if subcls is None:
            valid = ", ".join(cls._registry.keys())
            raise ValueError(
                f"Unknown {cls.__name__} provider name '{provider_name}'. Available: {valid}"
            )
        return subcls(**kwargs)


__all__ = ["LIStandard"]