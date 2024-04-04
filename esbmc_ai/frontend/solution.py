# Author: Yiannis Charalambous

"""# Solution
Keeps track of all the source files that ESBMC-AI is targeting."""

from typing import NamedTuple


class SourceFile(NamedTuple):
    file_path: str
    content: str


_main_source_file: SourceFile = SourceFile("", "")
_source_files: set[SourceFile] = set()


def add_source_file(source_file: SourceFile) -> None:
    global _source_files
    _source_files.add(source_file)


def set_main_source_file(source_file: SourceFile) -> None:
    add_source_file(source_file)
    global _main_source_file
    _main_source_file = source_file


def get_main_source_file_path() -> str:
    global _main_source_file
    return _main_source_file.file_path


def get_main_source_file() -> SourceFile:
    global _main_source_file
    return _main_source_file


def get_source_files() -> list[SourceFile]:
    global _source_files
    return list(_source_files)


def apply_line_patch(source_code: str, patch: str, start: int, end: int) -> str:
    """Applies a patch to the source code.

    To replace a single line, start and end are equal.

    Args:
        * source_code - The source code to apply the patch to.
        * patch - Can be a line or multiple lines but will replace the start and
        end region defined.
        * start - Line index to mark start of replacement.
        * end - Marks the end of the region where the patch will be applied to.
        End is non-inclusive."""
    assert (
        start <= end
    ), f"start ({start}) needs to be less than or equal to end ({end})"
    lines: list[str] = source_code.splitlines()
    lines = lines[:start] + [patch] + lines[end + 1 :]
    return "\n".join(lines)
