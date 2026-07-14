from functools import lru_cache

from ..config import EXTRACTOR_MODE
from .base import Extractor


@lru_cache(maxsize=1)
def get_extractor() -> Extractor:
    if EXTRACTOR_MODE == "anthropic":
        from .anthropic_extractor import AnthropicExtractor
        return AnthropicExtractor()
    from .mock import MockExtractor
    return MockExtractor()
