# Author: Yiannis Charalambous

from typing import Callable
from typing_extensions import override
from esbmc_ai_config.context_manager import ContextManager
from esbmc_ai_config.contexts.base_menu import BaseMenu

import urwid


class ListSelectDialog(BaseMenu):
    def __init__(
        self,
        title: str,
        options: list[str],
        item_selected: Callable[[str], None],
        initial_choice: int = 0,
    ) -> None:
        super().__init__(
            title=title,
            choices=list(options),
            back_choice=True,
            initial_choice=initial_choice,
        )

        self.item_selected: Callable[[str], None] = item_selected

    @override
    def item_chosen(self, button: urwid.Button, choice: list[str]) -> None:
        if choice in self.choices:
            self.item_selected(choice)
        ContextManager.pop_context()

    @override
    def build_ui(self) -> urwid.Widget:
        # Update value of choices to contain new objects of TextInputButton
        # with initial values.
        self.choices: list[str | urwid.Widget] = self.choices
        # Build the BaseMenu UI.
        menu: urwid.Widget = super().build_ui()
        # Wrap in nice UI.
        overlay: urwid.Widget = urwid.Overlay(
            urwid.LineBox(menu),
            urwid.SolidFill("\N{MEDIUM SHADE}"),
            align="center",
            valign="middle",
            width=("relative", 60),
            height=("relative", 15),
            min_width=20,
            min_height=10,
        )

        return overlay
