# Author: Yiannis Charalambous

"""Logging module for verbose printing."""

verbose: int = 0


def set_verbose(level: int) -> None:
    """Sets the verbosity level."""
    global verbose
    verbose = level


def printv(m) -> None:
    """Level 1 verbose printing."""
    if verbose > 0:
        print(m)


def printvv(m) -> None:
    """Level 2 verbose printing."""
    if verbose > 1:
        print(m)


def printvvv(m) -> None:
    """Level 3 verbose printing."""
    if verbose > 2:
        print(m)
