# Author: Yiannis Charalambous

from typing_extensions import override

import urwid
from esbmc_ai_config.context import Context
from esbmc_ai_config.context_manager import ContextManager


class DialogContext(Context):
    def __init__(self, title: str = "", message: str = "") -> None:
        self.title: str = title
        self.message: str = message

        super().__init__()

    def _on_ok(self, button) -> None:
        ContextManager.pop_context()

    @override
    def build_ui(self) -> urwid.Widget:
        ok_button: urwid.Button = urwid.Button("OK", on_press=self._on_ok)

        body: list[urwid.Widget] = [
            urwid.Text(self.title),
            urwid.Divider(),
            urwid.Text(self.message),
            urwid.Divider(),
            urwid.Columns([urwid.AttrMap(ok_button, None, focus_map="reversed")]),
        ]

        list_menu: urwid.ListBox = urwid.ListBox(body)
        # Wrap in nice UI.
        overlay: urwid.Widget = urwid.Overlay(
            urwid.LineBox(urwid.Padding(list_menu, left=2, right=2)),
            urwid.SolidFill("\N{MEDIUM SHADE}"),
            align="center",
            valign="middle",
            width=("relative", 60),
            height=("relative", 15),
            min_width=20,
            min_height=10,
        )
        return overlay
