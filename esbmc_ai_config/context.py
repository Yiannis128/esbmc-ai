# Author: Yiannis Charalambous

from abc import abstractmethod
from typing import Optional
import urwid


class Context(urwid.WidgetWrap):
    def __init__(self, widget: Optional[urwid.Widget] = None) -> None:
        super().__init__(widget if widget else self.build_ui())

    @property
    def widget(self) -> urwid.Widget:
        assert isinstance(self._wrapped_widget, urwid.Widget)
        return self._wrapped_widget

    @widget.setter
    def widget(self, value: urwid.Widget) -> None:
        self._wrapped_widget = value

    @abstractmethod
    def build_ui(self) -> urwid.Widget:
        """Provides a method to build the interface, if not provided."""
        raise NotImplementedError

    def refresh_ui(self) -> None:
        self.widget = self.build_ui()
