import os


def get_terminal_width(default: int = 10) -> int:
    width: int
    try:
        width = os.get_terminal_size().columns
    except OSError:
        width = default

    return width
