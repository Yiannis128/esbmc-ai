# Author: Yiannis Charalambous 2023

"""
  This program is designed to create
  and animate a simple loading animation.
  Original source: https://gist.github.com/rudrathegreat/b11daed176c8119dcedbb6b06c953590
"""

from sys import stdout as terminal
from time import sleep
from itertools import cycle
from threading import Thread
from typing import Optional

from esbmc_ai import config


class LoadingWidget(object):
    done: bool = False
    thread: Optional[Thread]
    loading_text: str
    animation: list[str]
    anim_speed: float
    anim_clear_length: int

    def __init__(
        self,
        anim_speed: float = 0.1,
        animation: list[str] = ["|", "/", "-", "\\"],
    ) -> None:
        super().__init__()
        self.anim_speed = anim_speed
        self.animation = animation

        # Find the largest animatioon
        self.anim_clear_length = 0
        for frame in self.animation:
            if len(frame) > self.anim_clear_length:
                self.anim_clear_length = len(frame)

    def _animate(self) -> None:
        for c in cycle(self.animation):
            if self.done:
                break
            # Calculate how much extra space to clear after c.
            extra_space_clear: int = self.anim_clear_length - len(c)
            terminal.write(f"\r{self.loading_text} " + c + " " * extra_space_clear)
            terminal.flush()
            sleep(self.anim_speed)

        # +1 for space between loading text and c.
        clear_length: int = len(self.loading_text) + 1 + self.anim_clear_length
        terminal.write("\r" + " " * clear_length)
        terminal.flush()
        terminal.write("\r")
        terminal.flush()

    def start(self, text: str = "Please Wait") -> None:
        if not config.loading_hints:
            return
        self.done = False
        self.loading_text = text
        self.thread = Thread(target=self._animate)
        self.thread.daemon = True
        self.thread.start()

    def stop(self) -> None:
        if not config.loading_hints:
            return
        self.done = True
        # Block until end.
        if self.thread:
            self.thread.join()


_widgets: list[LoadingWidget] = []


def create_loading_widget(
    anim_speed: float = 0.1,
    animation: list[str] = ["|", "/", "-", "\\"],
) -> LoadingWidget:
    w = LoadingWidget(anim_speed=anim_speed, animation=animation)
    _widgets.append(w)
    return w


def stop_all() -> None:
    for w in _widgets:
        w.stop()
