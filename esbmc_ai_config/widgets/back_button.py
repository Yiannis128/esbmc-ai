# Author: Yiannis Charalambous

import urwid
from urwid.widget import Button

from esbmc_ai_config.context_manager import ContextManager


class BackButton(urwid.WidgetWrap):
    def __init__(self):
        super().__init__(self.build_ui())

    def _on_pressed(self, button) -> None:
        ContextManager.pop_context()

    def build_ui(self) -> urwid.Widget:
        self.button: urwid.Button = Button(
            "Back",
            on_press=self._on_pressed,
        )
        return urwid.AttrMap(self.button, None, focus_map="reversed")
