# Author: Yiannis Charalambous

from urwid import MainLoop

from esbmc_ai_config.context import Context


class ContextManager(object):
    app: MainLoop
    view_stack: list[Context] = []

    def __init__(self) -> None:
        raise Exception("Static class cannot be instantiated...")

    @classmethod
    def init(cls, app: MainLoop, ctx: Context) -> None:
        cls.app = app
        cls.view_stack.append(ctx)
        cls.app.widget = ctx

    @classmethod
    def push_context(cls, ctx: Context) -> None:
        cls.view_stack.append(ctx)
        cls.app.widget = ctx

    @classmethod
    def pop_context(cls) -> Context:
        cls.app.widget = cls.view_stack[-2]
        return cls.view_stack.pop()

    @classmethod
    def get_context(cls) -> Context:
        return cls.view_stack[-1]
