# Author: Yiannis Charalambous

from typing_extensions import override

import urwid

from esbmc_ai.ai_models import AIModels

from esbmc_ai_config.models.config_manager import ConfigManager
from esbmc_ai_config.context_manager import ContextManager
from esbmc_ai_config.context import Context
from esbmc_ai_config.contexts.base_menu import BaseMenu
from esbmc_ai_config.contexts.list_select_dialog import ListSelectDialog


class AIConfigMenu(BaseMenu):
    def __init__(self) -> None:
        super().__init__(title="AI Configuration", choices=self._get_menu_choices())

    def _get_menu_choices(self) -> list[str | urwid.Widget]:
        return [
            urwid.AttrMap(
                urwid.Button(
                    "AI Model",
                    on_press=self._open_ai_model_dialog,
                ),
                None,
                "reversed",
            ),
            "Temperature",
            "API Request Cooldown",
        ]

    def _open_ai_model_dialog(self, button: urwid.Button) -> None:
        # Get built-in AI models.
        options: list[str] = [ai_model.value.name for ai_model in AIModels]
        ai_model = ConfigManager.json_config.get_value("ai_model")
        current_option: int = 0
        if isinstance(ai_model, str):
            current_option = options.index(ai_model)
        # TODO Load custom AI models
        dialog: Context = ListSelectDialog(
            title="AI Model",
            options=options,
            initial_choice=current_option,
            item_selected=lambda ai_model: ConfigManager.json_config.set_value(
                ai_model, "ai_model"
            ),
        )

        ContextManager.push_context(dialog)

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
