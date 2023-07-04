# Author: Yiannis Charalambous

import sys

from typing_extensions import override
from .chat_command import ChatCommand
from ..frontend import ast
from ..frontend.ast import FunctionDeclaration


class OptimizeCodeCommand(ChatCommand):
    def __init__(self) -> None:
        super().__init__(
            command_name="optimize-code",
            help_message="Optimizes the code of a specific function or the entire file if a function is not specified. Usage: optimize-code [function_name]",
        )

    @override
    def execute(
        self, file_path: str, source_code: str, function_names: list[str]
    ) -> None:
        clang_ast: ast.ClangAST = ast.ClangAST(
            file_path=file_path, source_code=source_code
        )

        all_functions: list[FunctionDeclaration] = clang_ast.get_function_declarations()
        all_function_names: list[str] = [fn.name for fn in all_functions]

        # If specific function names to optimize have been specified, then
        # check that they exist.
        if len(function_names) > 0:
            for function_name in function_names:
                if function_name not in all_function_names:
                    print(f"Error: {function_name} is not defined...")
                    sys.exit(1)
        else:
            function_names = all_function_names.copy()

        print(f"Optimizing the following functions: {function_names}")

        for function in function_names:
            print(f"\nOptimizing function: {function}")
            print("TODO")
