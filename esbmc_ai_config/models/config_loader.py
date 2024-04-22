# Author: Yiannis Charalambous


from abc import abstractmethod
import os


class ConfigLoader(object):
    """Class responsible for loading the ESBMC-AI config. Is generic so contains
    methods for EnvConfigLoader and JsonConfigLoader"""

    def __init__(
        self,
        file_path: str,
        create_missing_fields: bool = False,
        create_default_file: bool = False,
    ) -> None:
        """Initializes the config loader. Will expand the file_path macros. If the file
        does not exist or cannot be read, and create_default_file is True, then a new
        file will be created."""
        self.file_path: str = os.path.expanduser(os.path.expandvars(file_path))
        if os.path.exists(self.file_path) and os.path.isfile(self.file_path):
            with open(self.file_path, "r") as file:
                self.content: str = file.read()
        elif create_default_file:
            # Create default file.
            self._create_default_file()

        # Read fields.
        self._read_fields(create_missing_fields=create_missing_fields)

    @abstractmethod
    def _create_default_file(self) -> None:
        raise NotImplementedError()

    @abstractmethod
    def _read_fields(self, create_missing_fields: bool = False) -> None:
        raise NotImplementedError()

    @abstractmethod
    def save(self) -> None:
        raise NotImplementedError()
