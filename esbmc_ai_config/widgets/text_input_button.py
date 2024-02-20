# Author: Yiannis Charalambous

from typing import Callable, Optional

import urwid

from esbmc_ai_config.context import Context
from esbmc_ai_config.context_manager import ContextManager


class TextInputButton(urwid.WidgetWrap):
    def __init__(
        self,
        title: str,
        initial_value: str = "",
        create_cancel: bool = True,
        on_submit: Optional[Callable[[str, str, bool], None]] = None,
    ) -> None:
        """Button that when selected will open a dialog to enter text inside. The
        dialog has the OK, and optionally Cancel option."""
        button = urwid.Button(title)
        urwid.connect_signal(
            obj=button,
            name="click",
            callback=self.open_dialog,
        )

        # Reverse attributes when focused
        widget: urwid.Widget = urwid.AttrMap(button, None, focus_map="reversed")

        super().__init__(widget)

        self.title: str = title
        self.create_cancel: bool = create_cancel
        self.on_submit = on_submit
        """Callback for when the input dialog is concluded.
        
        Args:
            str - Title of dialog.
            str - The value of the dialog.
            bool - True if ok else False for cancel."""
        self.initial_value: str = initial_value

    def _on_dialog_button_selected(
        self,
        button: urwid.Widget,
        ok_pressed: bool,
    ) -> None:
        # Close dialog
        ContextManager.pop_context()

        if self.on_submit:
            self.on_submit(self.title, self.edit_widget.edit_text, ok_pressed)

    def open_dialog(self, button: urwid.Widget) -> None:
        # Create overlay menu with question.

        self.ok_button: urwid.Button = urwid.Button(
            "OK",
            on_press=self._on_dialog_button_selected,
            user_data=True,
        )
        self.edit_widget: urwid.Edit = urwid.Edit(
            caption="Value: ",
            edit_text=self.initial_value,
        )

        body: list[urwid.Widget] = [
            urwid.Text(self.title),
            urwid.Divider(),
            urwid.LineBox(self.edit_widget),
            urwid.Divider(),
        ]

        if self.create_cancel:
            self.cancel_button: urwid.Button = urwid.Button(
                "Cancel",
                on_press=self._on_dialog_button_selected,
                user_data=False,
            )
            body.append(urwid.AttrMap(self.cancel_button, None, focus_map="reversed"))

        body.append(urwid.AttrMap(self.ok_button, None, focus_map="reversed"))

        listbox: urwid.ListBox = urwid.ListBox(urwid.SimpleFocusListWalker(body))

        overlay: urwid.Widget = urwid.Overlay(
            urwid.LineBox(
                urwid.Padding(
                    listbox,
                    left=2,
                    right=2,
                ),
            ),
            ContextManager.get_context(),
            align="center",
            valign="middle",
            width=("relative", 60),
            height=("relative", 15),
            min_width=20,
            min_height=12,
        )

        ContextManager.push_context(Context(overlay))
