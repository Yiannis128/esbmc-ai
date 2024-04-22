# Author: Yiannis Charalambous

from typing_extensions import override

import urwid
from esbmc_ai_config.context_manager import ContextManager
from esbmc_ai_config.contexts.base_menu import BaseMenu
from esbmc_ai_config.contexts.esbmc_menu.esbmc_manage import ESBMCManage
from esbmc_ai_config.widgets.text_input_button import TextInputButton
from esbmc_ai_config.models.config_manager import ConfigManager


class ESBMCMenu(BaseMenu):
    def __init__(self) -> None:
        super().__init__(title="ESBMC Options", choices=self._get_menu_choices())

    def _on_esbmc_path(self, title: str, value: str, ok_pressed: bool) -> None:
        if ok_pressed:
            ConfigManager.json_config.set_value(value, "esbmc_path")
            # Refresh UI
            self.refresh_ui()

    def _get_menu_choices(self) -> list[str | urwid.Widget]:
        return [
            urwid.AttrMap(
                urwid.Button(
                    "Install ESBMC",
                    on_press=lambda _: ContextManager.push_context(ESBMCManage()),
                ),
                None,
                "reversed",
            ),
            TextInputButton(
                "ESBMC Path",
                str(ConfigManager.json_config.get_value("esbmc_path")),
                on_submit=self._on_esbmc_path,
            ),
            "ESBMC Parameters",
        ]

    @override
    def build_ui(self) -> urwid.Widget:
        self.choices = self._get_menu_choices()
        menu: urwid.Widget = super().build_ui()
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
