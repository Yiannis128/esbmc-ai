# Author: Yiannis Charalambous


from typing_extensions import override
import urwid
from urwid import Text, Widget

from esbmc_ai_config.context_manager import ContextManager
from esbmc_ai_config.contexts import BaseMenu
from esbmc_ai_config.contexts.ai_config_menu import AIConfigMenu
from esbmc_ai_config.contexts.save_menu import SaveMenu
from esbmc_ai_config.contexts.env_menu import EnvMenu
from esbmc_ai_config.contexts.esbmc_menu import ESBMCMenu


class MainMenu(BaseMenu):
    def __init__(self) -> None:
        super().__init__(
            title="Main Menu",
            choices=[
                "Setup Environment",
                "ESBMC Settings",
                "AI Configuration",
                "Custom LLM",
                urwid.Divider(),
                "Save",
                "Save As",
                urwid.Divider(),
                "Exit",
            ],
            back_choice=False,
        )

    @override
    def build_ui(self) -> urwid.Widget:
        list_menu: urwid.Widget = super().build_ui()
        # Add additional content to widget.
        text = urwid.ListBox(
            [
                Text(
                    "ESBMC-AI CLI Configuration Tool\n"
                    "Made by Yiannis Charalambous\n\n"
                    "This tool configures ESBMC-AI through CLI menus using the ncurses library."
                    "Not all options may be available, so it is worth checking the documentation:\n\n"
                    "https://github.com/Yiannis128/esbmc-ai/wiki/Configuration\n\n"
                    "Env File:    ~/.config/esbmc-ai.env\n"
                    "Config File: ~/.config/esbmc-ai.json\n\n"
                    "Control Keys:\n"
                    "- Up/Down:     Navigation\n"
                    "- Enter:       Select Option\n"
                )
            ]
        )

        top: Widget = urwid.Overlay(
            urwid.LineBox(list_menu),
            text,
            align="center",
            valign="middle",
            width=("relative", 60),
            height=("relative", 15),
            min_width=20,
            min_height=14,
        )

        return top

    @override
    def item_chosen(self, button, choice) -> None:
        super().item_chosen(button, choice)

        match choice:
            case "Exit":
                self.exit_program(button)
            case "Setup Environment":
                ContextManager.push_context(EnvMenu())
                return
            case "ESBMC Settings":
                ContextManager.push_context(ESBMCMenu())
                return
            case "AI Configuration":
                ContextManager.push_context(AIConfigMenu())
            case "Save":
                ContextManager.push_context(SaveMenu())
                return

    def exit_program(self, _):
        raise urwid.ExitMainLoop()
