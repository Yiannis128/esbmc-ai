# Author: Yiannis Charalambous

import os
import sys
from typing import Optional, Tuple
from typing_extensions import override
from string import Template
from random import randint

from esbmc_ai_lib.term import get_terminal_width
from esbmc_ai_lib.chat_response import json_to_base_messages
from esbmc_ai_lib.frontend.ast_decl import Declaration, TypeDeclaration
from esbmc_ai_lib.frontend.c_types import is_primitive_type, get_base_type
from esbmc_ai_lib.frontend.esbmc_code_generator import ESBMCCodeGenerator
from esbmc_ai_lib.esbmc_util import esbmc_load_source_code
from esbmc_ai_lib.msg_bus import Signal
from esbmc_ai_lib.solution_generator import SolutionGenerator
from .chat_command import ChatCommand
from .. import config
from ..base_chat_interface import ChatResponse
from ..optimize_code import OptimizeCode
from ..frontend import ast
from ..frontend.ast import ClangAST, FunctionDeclaration
from ..logging import printvv


class OptimizeCodeCommand(ChatCommand):
    eq_script_path: str = "scripts/function_equivalence.c"

    def __init__(self) -> None:
        super().__init__(
            command_name="optimize-code",
            help_message="(EXPERIMENTAL) Optimizes the code of a specific function or the entire file if a function is not specified. Usage: optimize-code [function_name]",
        )
        self.on_solution_signal: Signal = Signal()

    @staticmethod
    def _generate_param_name(d: Declaration) -> str:
        return f"param_{d.type_name.replace(' ', '_').replace('*', 'ptr')}_{randint(a=0, b=99999)}"

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

    def _generate_primitive_type_variables(
        self,
        elements: list[Declaration],
        code_gen: ESBMCCodeGenerator,
        max_depth: int = 10,
        _current_depth: int = -1,
    ) -> tuple[list[str], list[str]]:
        """Generates the initialization values for a list of Declarations.
        Starts by traversing the parameters of a function depth first, as soon
        as a primitive type is reached, a variable is initialized using
        __VERIFIER_nondet_X() as the value.
        The names of the variables, along with the declaration statement is returned."""

        ast: ClangAST = code_gen.ast

        names: list[str] = []
        statements: list[str] = []

        _current_depth += 1

        for arg in elements:
            assert arg.cursor, f"Element {elements} has no valid cursor."

            if is_primitive_type(arg):
                name: str = OptimizeCodeCommand._generate_param_name(arg)
                statement = code_gen.statement_primitive_construct(
                    d=arg,
                    assign_to=name,
                    init=True,
                )
                names.append(name)
                statements.append(statement)
            else:
                arg_type: Optional[
                    TypeDeclaration
                ] = ast._get_type_declaration_from_cursor(arg.cursor)
                assert arg_type, f"Assert failed: {arg}"

                if _current_depth < max_depth:
                    # Traverse tree
                    n, s = self._generate_primitive_type_variables(
                        elements=arg_type.elements,
                        code_gen=code_gen,
                        max_depth=max_depth,
                        _current_depth=_current_depth,
                    )

                    names.extend(n)
                    statements.extend(s)
                else:
                    # Generate NULL
                    names.append("NULL")
                    statements.append("")

        return names, statements

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

        def rename_append_declaration(ast: ast.ClangAST, append: str):
            """Appends a string to all declarations related to the passed one in an AST"""
            declarations: list[Declaration] = ast.get_all_decl()
            for declaration in declarations:
                ast.rename_declaration(
                    declaration=declaration,
                    new_name=declaration.name + append,
                )

        # Rename all elements from each code by appending _old and _new to names.
        rename_append_declaration(old_ast, "_old")

        # Update reference to old_function
        old_fns: list[FunctionDeclaration] = old_ast.get_fn_decl()
        for old_fn in old_fns:
            if old_fn.name == old_function.name + "_old":
                old_function = old_fn
                break

        # Rename new functions
        rename_append_declaration(new_ast, "_new")

        # Update reference to new_function
        new_fns: list[FunctionDeclaration] = new_ast.get_fn_decl()
        for new_fn in new_fns:
            if new_fn.name == new_function.name + "_new":
                new_function = new_fn
                break

        # Assume that if old_function and new_function are equal before the
        # rename, they are equal after the rename, so no need to check
        # old_ast and new_ast after the rename.

        # Generate the code
        code_gen_old: ESBMCCodeGenerator = ESBMCCodeGenerator(old_ast)
        code_gen_new: ESBMCCodeGenerator = ESBMCCodeGenerator(new_ast)

        # Generate parameters using same function call of __VERIFIER_nondet_X for primitives.
        # The parameters will be inlined into the function.

        # Variable names of primitive values.
        primitive_vars_names: list[str] = []
        # Declaration statements for the variables
        statements: list[str] = []
        primitive_vars_names, statements = self._generate_primitive_type_variables(
            elements=old_function.args,
            code_gen=code_gen_old,
            max_depth=config.ocm_init_max_depth,
        )

        # Function parameters.
        fn_params_old: list[str] = []
        fn_params_new: list[str] = []

        # Generate function parameter values.
        param_idx: int = 0
        for arg_old, arg_new in zip(old_function.args, new_function.args):
            # Convert to type
            assert arg_old.cursor and arg_new.cursor

            # If it's a primitive type, then no need to call the code generator,
            # can simply add name of primitive value.
            if is_primitive_type(arg_old):
                fn_params_old.append(primitive_vars_names[param_idx])
                fn_params_new.append(primitive_vars_names[param_idx])
                param_idx += 1
            else:
                if arg_old.is_pointer_type():
                    pass

                arg_old_type: Optional[
                    TypeDeclaration
                ] = old_ast._get_type_declaration_from_cursor(arg_old.cursor)
                arg_new_type: Optional[
                    TypeDeclaration
                ] = new_ast._get_type_declaration_from_cursor(arg_new.cursor)
                assert (
                    arg_old_type and arg_new_type
                ), f"Assert failed: {arg_old} or {arg_new}"

                # Create statements and save them.
                statement_old = code_gen_old.statement_type_construct(
                    d_type=arg_old_type,
                    init_type="ptr" if arg_old.is_pointer_type() else "value",
                    init=False,
                    primitive_assignment_fn=lambda _: primitive_vars_names[param_idx],
                    max_depth=config.ocm_init_max_depth,
                )
                fn_params_old.append(statement_old)

                statement_new = code_gen_new.statement_type_construct(
                    d_type=arg_new_type,
                    init_type="ptr" if arg_new.is_pointer_type() else "value",
                    init=False,
                    primitive_assignment_fn=lambda _: primitive_vars_names[param_idx],
                    max_depth=config.ocm_init_max_depth,
                )
                fn_params_new.append(statement_new)

                param_idx += 1

        # Generate the function call & arguments
        old_params_src: str = code_gen_old.statement_function_call(
            fn=old_function,
            assign_to="old_fn_result",
            params=fn_params_old,
            init=True,
        )
        new_params_src: str = code_gen_new.statement_function_call(
            fn=new_function,
            assign_to="new_fn_result",
            params=fn_params_new,
            init=True,
        )

        # TODO Dereference fn result if pointer.

        script: str = template.substitute(
            function_old=old_ast.source_code,
            function_new=new_ast.source_code,
            parameters_list="\n".join(statements),
            function_call_old=old_params_src,
            function_call_new=new_params_src,
            function_assert_old="old_fn_result",
            function_assert_new="new_fn_result",
        )

        return script

    def check_function_pequivalence(
        self,
        original_source_code: str,
        new_source_code: str,
        function_name: str,
    ) -> bool:
        """Function partial equivalence checking. Checks if the `function_name`
        function exists in `original_source_code` and `new_source_code`. Then,
        builds a comparison script and checks it with ESBMC."""

        original_ast: ast.ClangAST = ast.ClangAST(
            file_path="old.c",
            source_code=original_source_code,
        )

        new_ast: ast.ClangAST = ast.ClangAST(
            file_path="new.c",
            source_code=new_source_code,
        )

        # Get list of function types.
        old_functions: list[FunctionDeclaration] = original_ast.get_fn_decl()
        new_functions: list[FunctionDeclaration] = new_ast.get_fn_decl()

        # First get original function declaration from source code.
        old_function: Optional[FunctionDeclaration] = None
        for fn in old_functions:
            if fn.name == function_name:
                old_function = fn

        if old_function is None:
            return False

        # Check that the new functions set also has this function. The equivalence of
        # function declarations will ensure that args are also checked.
        new_function: Optional[FunctionDeclaration] = None
        for fn in new_functions:
            if old_function == fn:
                new_function = fn

        if new_function is None:
            print(f"Error: Could not match new function to old one...")
            return False

        esbmc_script: str = self._build_comparison_script(
            old_ast=original_ast,
            new_ast=new_ast,
            old_function=old_function,
            new_function=new_function,
        )

        # Run script with ESBMC.
        save_path: str = os.path.join(
            config.temp_file_dir, os.path.basename(self.eq_script_path)
        )

        # Ignore ESBMC stdout and stderr
        esbmc_exit_code, _, _ = esbmc_load_source_code(
            file_path=save_path,
            source_code=esbmc_script,
            esbmc_params=config.esbmc_params_optimize_code,
            auto_clean=config.temp_auto_clean,
        )

        return esbmc_exit_code == 0

    @override
    def execute(
        self,
        file_path: str,
        source_code: str,
        function_names: list[str],
    ) -> Tuple[bool, str]:
        """Executes the Optimize Code command. The command takes the following inputs:
        * file_path: The path of the source code file.
        * source_code: The source code file contents.
        * function_names: List of function names to optimize. Main is always excluded.

        Returns a `Tuple[bool, str]` which is the flag if there was an error, and the
        source code from the LLM.
        """
        clang_ast: ast.ClangAST = ast.ClangAST(
            file_path=file_path,
            source_code=source_code,
        )

        try:
            function_names = self._get_functions_list(clang_ast, function_names)
            # Remove main method if it exists.
            if "main" in function_names:
                function_names.remove("main")
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

                optimized_source_code: str = SolutionGenerator.get_code_from_solution(
                    response.message.content
                )

                printvv(f"\nGeneration ({fn_name}):")
                printvv("-" * get_terminal_width())
                printvv(optimized_source_code)
                printvv("-" * get_terminal_width())

                # Check equivalence
                equal: bool = self.check_function_pequivalence(
                    original_source_code=source_code,
                    new_source_code=optimized_source_code,
                    function_name=fn_name,
                )

                if equal:
                    # If equal, then return with explanation.
                    new_source_code = optimized_source_code
                    break
                elif attempt == max_retries - 1:
                    return True, "Failed all attempts..."
                else:
                    print("Failed attempt", attempt)

        return False, new_source_code
