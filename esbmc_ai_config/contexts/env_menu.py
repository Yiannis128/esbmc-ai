# Author: Yiannis Charalambous

from typing_extensions import override
import urwid
from esbmc_ai_config.models.config_manager import ConfigManager

from esbmc_ai_config.models import EnvConfigField
from esbmc_ai_config.contexts.base_menu import BaseMenu
from esbmc_ai_config.widgets.text_input_button import TextInputButton


class EnvMenu(BaseMenu):
    def __init__(self) -> None:
        super().__init__(title="Setup Environment", choices=self._get_menu_items())

    def _get_menu_items(self) -> list[str | urwid.Widget]:
        choices: list[str | urwid.Widget] = [
            TextInputButton(
                field.name,
                on_submit=self._on_value_submit,
                initial_value=str(ConfigManager.env_config.values[field.name]),
            )
            for field in ConfigManager.env_config.fields
            if field.show_in_config
        ]
        return choices

    @override
    def build_ui(self) -> urwid.Widget:
        # Update value of choices to contain new objects of TextInputButton
        # with initial values.
        self.choices: list[str | urwid.Widget] = self._get_menu_items()
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

    def _on_value_submit(self, title: str, value: str, ok_pressed: bool) -> None:
        if ok_pressed:
            # Find the correct field.
            field: EnvConfigField
            for i in ConfigManager.env_config.fields:
                if i.name == title:
                    field = i
                    break
            else:
                return

            # Cast to the correct type.
            ConfigManager.env_config.values[title] = type(field.default_value)(value)
            self.refresh_ui()
