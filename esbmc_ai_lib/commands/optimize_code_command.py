# Author: Yiannis Charalambous

import os
import sys
from os import get_terminal_size
from typing import Optional
from typing_extensions import override
from string import Template

from clang.cindex import TranslationUnit

from esbmc_ai_lib.chat_response import json_to_base_messages
from esbmc_ai_lib.frontend.ast_decl import InclusionDirective
from .chat_command import ChatCommand
from .. import config
from ..base_chat_interface import ChatResponse
from ..optimize_code import OptimizeCode
from ..frontend import ast
from ..frontend.ast import FunctionDeclaration
from ..logging import printvv


class OptimizeCodeCommand(ChatCommand):
    eq_script_path: str = "scripts/function_equivalence.c"

    def __init__(self) -> None:
        super().__init__(
            command_name="optimize-code",
            help_message="Optimizes the code of a specific function or the entire file if a function is not specified. Usage: optimize-code [function_name]",
        )

    def _get_functions_list(
        self,
        clang_ast: ast.ClangAST,
        function_names: list[str],
    ) -> list[str]:
        """Returns the functions that are referenced in the specified `clang_ast`.

        If the array is empty, then the entire list of function names in
        `clang_ast` is returned. If a subset of the functions in `clang_ast` is
        specified, then that is checked against the functions of `clang_ast` and
        returned. If there's a function specified that is not inside `clang_ast`
        then a `ValueError` is raised."""
        all_function_names: list[str] = [fn.name for fn in clang_ast.get_fn_decl()]

        # If specific function names to optimize have been specified, then
        # check that they exist.
        if len(function_names) > 0:
            for function_name in function_names:
                if function_name not in all_function_names:
                    raise ValueError(f"Error: {function_name} is not defined...")
        else:
            function_names = all_function_names.copy()
        return function_names

    def _build_comparison_script(
        self,
        old_ast: ast.ClangAST,
        new_ast: ast.ClangAST,
        old_function: FunctionDeclaration,
        new_function: FunctionDeclaration,
    ) -> str:
        """Builds an ESBMC C source code script that insturcts ESBMC to compare the two functions
        together. A script template is used."""

        # Load and replace template.
        with open(self.eq_script_path, "r") as file:
            template_str: str = file.read()
        template: Template = Template(template=template_str)

        # Get includes from both files, and include it
        includes: set[InclusionDirective] = set(old_ast.get_include_directives())
        includes.update(new_ast.get_include_directives())

        # Get source code of old and new functions.
        old_source_code: str = old_ast.get_source_code(declaration=old_function)
        new_source_code: str = new_ast.get_source_code(declaration=new_function)

        # Modify names of underlying cursor before generating source code.
        # TODO Use rename function (when ready)
        old_source_code = old_source_code.replace(
            old_function.name, old_function.name + "_old", 1
        )
        new_source_code = new_source_code.replace(
            new_function.name, new_function.name + "_new", 1
        )

        # TODO Add global scope variables that old and new functions use.
        # TODO Global scope variables will need to be renamed with new and old appended to their
        # names.

        # TODO build parameter list

        script: str = template.substitute(
            function_old=old_source_code,
            function_new=new_source_code,
            includes="\n".join([str(include) for include in includes]),
        )

        return script

    def check_function_equivalence(
        self,
        original_source_code: str,
        new_source_code: str,
        function_name: str,
    ) -> bool:
        """Function equivalence checking"""

        original_ast: ast.ClangAST = ast.ClangAST(
            file_path="old.c",
            source_code=original_source_code,
        )

        new_ast: ast.ClangAST = ast.ClangAST(
            file_path="new.c",
            source_code=new_source_code,
        )

        # Get list of function types.
        orig_functions: set[FunctionDeclaration] = set(original_ast.get_fn_decl())
        new_functions: set[FunctionDeclaration] = set(new_ast.get_fn_decl())

        # Need to ensure that the functions have the same composition:

        # First get original function declaration from source code.
        old_function: Optional[FunctionDeclaration] = None
        for fn in orig_functions:
            if fn.name == function_name:
                old_function = fn
                break

        # Check that the new functions set also has this function. The equivalence of
        # function declarations will ensure that args are also checked.
        if old_function is None or old_function not in new_functions:
            return False

        # Get new function
        new_function: Optional[FunctionDeclaration] = None
        for fn in new_functions:
            # The old function and new function are identical, except they have different
            # underlying cursors.
            if fn == old_function:
                new_function = fn
                break

        if new_function is None:
            # TODO handle properly
            raise Exception()

        esbmc_script: str = self._build_comparison_script(
            old_ast=original_ast,
            new_ast=new_ast,
            old_function=old_function,
            new_function=new_function,
        )

        # TODO Run script with ESBMC.
        save_path: str = os.path.join(
            config.temp_file_dir, os.path.basename(self.eq_script_path)
        )
        with open(save_path, "w") as file:
            file.write(esbmc_script)

        # TODO Remove me
        print(esbmc_script)
        exit(0)

        return True

    @override
    def execute(
        self, file_path: str, source_code: str, function_names: list[str]
    ) -> None:
        clang_ast: ast.ClangAST = ast.ClangAST(
            file_path=file_path,
            source_code=source_code,
        )

        try:
            function_names = self._get_functions_list(clang_ast, function_names)
        except ValueError as e:
            print(e)
            sys.exit(1)

        print(f"Optimizing the following functions: ", ", ".join(function_names), "\n")

        # Declare code optimizer chat.
        chat: OptimizeCode = OptimizeCode(
            system_messages=json_to_base_messages(
                config.chat_prompt_optimize_code.system_messages
            ),
            initial_message=config.chat_prompt_optimize_code.initial_prompt,
            ai_model=config.ai_model,
            llm=config.ai_model.create_llm(
                api_keys=config.api_keys,
                temperature=config.chat_prompt_optimize_code.temperature,
            ),
        )

        # Loop through every function and generate an improvement.
        new_source_code: str = source_code
        max_retries: int = 10
        for fn_name in function_names:
            for attempt in range(max_retries):
                print(f"Optimizing function: {fn_name}")
                # Optimize the function
                response: ChatResponse = chat.optimize_function(
                    source_code=new_source_code,
                    function_name=fn_name,
                )

                printvv(f"\nGeneration ({fn_name}):")
                printvv("-" * get_terminal_size().columns)
                printvv(response.message.content)
                printvv("-" * get_terminal_size().columns)

                # Check equivalence
                # TODO Get response.message.content code extracted
                # using the method of solution generation.
                equal: bool = self.check_function_equivalence(
                    original_source_code=source_code,
                    new_source_code=response.message.content,
                    function_name=fn_name,
                )

                # TODO Handle cases where all attempts are failed.
                if equal:
                    new_source_code = response.message.content
                    break
                else:
                    print("Failed attempt", attempt)

        print("\nOptimizations Completed:\n")
        print(new_source_code)
        print()
