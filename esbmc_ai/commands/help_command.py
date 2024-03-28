# Author: Yiannis Charalambous

from typing import Any, Optional
from typing_extensions import override
from .chat_command import ChatCommand


class HelpCommand(ChatCommand):
    commands: list[ChatCommand] = []

    def __init__(self) -> None:
        super().__init__(
            command_name="help",
            help_message="Print this help message.",
        )

    def set_commands(self, commands: list[ChatCommand]) -> None:
        self.commands = commands

    @override
    def execute(self, **_: Optional[Any]) -> Optional[Any]:
        print()
        print("Commands:")

        for command in self.commands:
            print(f"/{command.command_name}: {command.help_message}")

        print()
        print("Useful AI Questions:")
        print("1) How can I correct this code?")
        print("2) What is the line with the error?")
        print("3) What is the exact error?")
        print()
