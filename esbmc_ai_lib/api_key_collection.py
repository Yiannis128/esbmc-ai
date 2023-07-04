# Author: Yiannis Charalambous

"""API Key Collection definition."""

from typing import NamedTuple


class APIKeyCollection(NamedTuple):
    """Class that is used to pass keys to AIModels."""

    openai: str = ""
    huggingface: str = ""
