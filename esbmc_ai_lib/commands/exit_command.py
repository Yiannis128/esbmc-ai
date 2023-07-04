# Author: Yiannis Charalambous

import sys

from typing_extensions import override
from .chat_command import ChatCommand


class ExitCommand(ChatCommand):
    def __init__(self) -> None:
        super().__init__(
            command_name="exit",
            help_message="Exit the program.",
        )

    @override
    def execute(self) -> None:
        print("exiting...")
        sys.exit(0)
