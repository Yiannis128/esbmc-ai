# Author: Yiannis Charalambous

from typing_extensions import override

import urwid
from esbmc_ai_config.context import Context
from esbmc_ai_config.context_manager import ContextManager
from esbmc_ai_config.contexts.dialog_context import DialogContext
from esbmc_ai_config.models import ConfigManager


class SaveMenu(Context):
    def __init__(self) -> None:
        super().__init__()

    def _on_cancel(self, button) -> None:
        ContextManager.pop_context()

    def _on_ok(self, button) -> None:
        ContextManager.pop_context()
        ConfigManager.env_config.save()
        ConfigManager.json_config.save()
        ContextManager.push_context(
            DialogContext(
                "Success",
                "ESBMC-AI Env and Config have been written successfully!",
            )
        )

    @override
    def build_ui(self) -> urwid.Widget:
        cancel_button: urwid.Button = urwid.Button("Cancel", on_press=self._on_cancel)
        ok_button: urwid.Button = urwid.Button("OK", on_press=self._on_ok)

        body: list[urwid.Widget] = [
            urwid.Text("Confirm"),
            urwid.Divider(),
            urwid.Text("Are you sure you want to save at location: "),
            urwid.Divider(),
            urwid.Columns(
                [
                    ("weight", 1, urwid.Divider()),
                    (
                        "weight",
                        2,
                        urwid.AttrMap(cancel_button, None, focus_map="reversed"),
                    ),
                    ("weight", 1, urwid.Divider()),
                    ("weight", 2, urwid.AttrMap(ok_button, None, focus_map="reversed")),
                    ("weight", 1, urwid.Divider()),
                ]
            ),
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
