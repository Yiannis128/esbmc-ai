# Author: Yiannis Charalambous


from typing import Optional
from pathlib import Path
from platform import system as system_name

from esbmc_ai_config.models.env_config_loader import EnvConfigLoader
from esbmc_ai_config.models.json_config_loader import JsonConfigLoader


class ConfigManager(object):
    env_config: EnvConfigLoader
    json_config: JsonConfigLoader

    def __init__(self) -> None:
        raise NotImplementedError("Cannot instantiate an abstract class.")

    @classmethod
    def init(
        cls, env_path: Optional[str] = None, config_path: Optional[str] = None
    ) -> None:
        cls.load_env(env_path)
        cls.load_json(config_path)

    @classmethod
    def load_json(cls, file_path: Optional[str] = None) -> None:
        if file_path:
            cls.json_config = JsonConfigLoader(
                file_path=file_path,
                create_missing_fields=True,
            )
        else:
            cls.json_config = JsonConfigLoader(
                create_missing_fields=True,
            )

    @classmethod
    def load_env(cls, file_path: Optional[str] = None) -> None:
        if file_path:
            cls.env_config = EnvConfigLoader(
                file_path,
                create_missing_fields=True,
            )
        else:
            cls.env_config = EnvConfigLoader(
                create_missing_fields=True,
            )

    @classmethod
    def get_esbmc_name(cls) -> str:
        if system_name() == "Windows":
            return "esbmc.exe"
        else:
            return "esbmc"

    @classmethod
    def get_esbmc_dir(cls) -> Path:
        if system_name() == "Windows":
            return Path.home() / "bin"
        else:
            return Path.home() / ".local/bin"

    @classmethod
    def get_esbmc_path(cls) -> Path:
        return cls.get_esbmc_dir() / cls.get_esbmc_name()
