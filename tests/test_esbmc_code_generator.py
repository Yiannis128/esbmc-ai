# Author: Yiannis Charalambous


from esbmc_ai_lib.frontend.ast import ClangAST
from esbmc_ai_lib.frontend.ast_decl import Declaration, TypeDeclaration
from esbmc_ai_lib.frontend.esbmc_code_generator import ESBMCCodeGenerator


def test_function_construct() -> None:
    source_code: str = """typedef int number;
int add(int a, int b) {
    return a + b;
}
number add_number(number a, number b) {
    return a + b;
}
void do_nothing() {}
typedef struct {
    int a;
    int b;
} col;
col create_col(number a, number b) {
    return (col){(int)a, (int)b};
}
"""

    answer_not_assign: list[str] = [
        "add(__VERIFIER_nondet_int(), __VERIFIER_nondet_int())",
        "add_number(__VERIFIER_nondet_int(), __VERIFIER_nondet_int())",
        "do_nothing()",
        "create_col(__VERIFIER_nondet_int(), __VERIFIER_nondet_int())",
    ]

    assign_to_name: str = "res"

    answer_assign_init: list[str] = [
        f"int {assign_to_name} = {answer_not_assign[0]};",
        f"number {assign_to_name} = {answer_not_assign[1]};",
        answer_not_assign[2] + ";",
        f"col {assign_to_name} = {answer_not_assign[3]};",
    ]

    ast: ClangAST = ClangAST("test.c", source_code)
    gen: ESBMCCodeGenerator = ESBMCCodeGenerator(ast)

    fns = ast.get_fn_decl()

    # Don't assign
    for idx, fn in enumerate(fns):
        result: str = gen.statement_function_call(fn=fn)
        assert result == answer_not_assign[idx]

    # Assign to
    for idx, fn in enumerate(fns):
        result: str = gen.statement_function_call(fn=fn, assign_to=assign_to_name)
        if fn.type_name != "void":
            assert result == assign_to_name + " = " + answer_not_assign[idx] + ";"
        else:
            assert answer_not_assign[idx] + ";"

    # Init the result
    for idx, fn in enumerate(fns):
        result: str = gen.statement_function_call(
            fn=fn,
            assign_to="" if fn.type_name == "void" else assign_to_name,
            init=True,
        )
        assert result == answer_assign_init[idx]


def test_statement_type_construct_inline() -> None:
    source_code: str = """struct abc {
    int a, b;
    char c;
};
struct abcd {
    struct abc abc_instance;
    long long int d;
};"""

    answers_inline: list[str] = [
        "(struct abc){__VERIFIER_nondet_int(),__VERIFIER_nondet_int(),__VERIFIER_nondet_char()}",
        "(struct abcd){(struct abc){__VERIFIER_nondet_int(),__VERIFIER_nondet_int(),__VERIFIER_nondet_char()},__VERIFIER_nondet_long()}",
    ]

    ast: ClangAST = ClangAST("test.c", source_code)
    code_gen: ESBMCCodeGenerator = ESBMCCodeGenerator(ast)

    types: list[TypeDeclaration] = ast.get_type_decl()

    # Inline tests
    for idx, t in enumerate(types):
        result: str = code_gen.statement_type_construct(
            d_type=t,
            init_type="value",
        )
        assert result == answers_inline[idx]


def test_statement_type_construct_assignment() -> None:
    source_code: str = """struct abc {
    int a, b;
    char c;
};
struct abcd {
    struct abc abc_instance;
    long long int d;
};"""

    answers: list[str] = [
        "abc_instance = (struct abc){__VERIFIER_nondet_int(),__VERIFIER_nondet_int(),__VERIFIER_nondet_char()};",
        "abcd_instance = (struct abcd){(struct abc){__VERIFIER_nondet_int(),__VERIFIER_nondet_int(),__VERIFIER_nondet_char()},__VERIFIER_nondet_long()};",
    ]

    var_names: list[str] = [
        "abc_instance",
        "abcd_instance",
    ]

    ast: ClangAST = ClangAST("test.c", source_code)
    code_gen: ESBMCCodeGenerator = ESBMCCodeGenerator(ast)

    types: list[TypeDeclaration] = ast.get_type_decl()

    # Assignment tests
    for idx, t in enumerate(types):
        result: str = code_gen.statement_type_construct(
            d_type=t,
            init_type="value",
            assign_to=var_names[idx],
            init=False,
        )
        assert result == answers[idx]


def test_statement_type_construct_assignment_with_init() -> None:
    source_code: str = """struct abc {
    int a, b;
    char c;
};
struct abcd {
    struct abc abc_instance;
    long long int d;
};"""

    var_names: list[str] = [
        "abc_instance",
        "abcd_instance",
    ]

    answers: list[str] = [
        "struct abc abc_instance = (struct abc){__VERIFIER_nondet_int(),__VERIFIER_nondet_int(),__VERIFIER_nondet_char()};",
        "struct abcd abcd_instance = (struct abcd){(struct abc){__VERIFIER_nondet_int(),__VERIFIER_nondet_int(),__VERIFIER_nondet_char()},__VERIFIER_nondet_long()};",
    ]

    ast: ClangAST = ClangAST("test.c", source_code)
    code_gen: ESBMCCodeGenerator = ESBMCCodeGenerator(ast)

    types: list[TypeDeclaration] = ast.get_type_decl()

    # Assignment tests with init
    for idx, t in enumerate(types):
        result: str = code_gen.statement_type_construct(
            d_type=t,
            init_type="value",
            assign_to=var_names[idx],
            init=True,
        )
        assert result == answers[idx]


def test_statement_type_construct_primitive_assignment() -> None:
    source_code: str = """struct abc {
    int a, b;
    char c;
};
struct abcd {
    struct abc abc_instance;
    long long int d;
};"""

    ast: ClangAST = ClangAST("test.c", source_code)
    code_gen: ESBMCCodeGenerator = ESBMCCodeGenerator(ast)

    types: list[TypeDeclaration] = ast.get_type_decl()

    # Test primitive assignment.
    type_checks: list[str] = ["int", "int", "char", "int", "int", "char", "long long"]

    def primitive_assignment_fn_test(d: Declaration) -> str:
        assert d.type_name == type_checks.pop(0)
        return code_gen.statement_primitive_construct(d)

    for t in types:
        code_gen.statement_type_construct(
            d_type=t,
            init_type="value",
            primitive_assignment_fn=primitive_assignment_fn_test,
        )


def test_statement_type_construct_ptr() -> None:
    source_code: str = """#define NULL 0
struct LinkedList
{
    int value;
    struct LinkedList *next;
};
"""

    ast: ClangAST = ClangAST("test.c", source_code)
    gen: ESBMCCodeGenerator = ESBMCCodeGenerator(ast)

    linked_list_type: TypeDeclaration = ast.get_type_decl()[0]

    gen.statement_type_construct(
        d_type=linked_list_type,
        init_type="value",
        assign_to="",
        init=True,
    )


def test_primitive_construct_value() -> None:
    source_code: str = """typedef int number;
int add(int a, int b) {
    return a + b;
}
number add_number(number a, number b) {
    return a + b;
}
void do_nothing() {}
typedef struct {
    int a;
    int b;
} col;
col create_col(number a, number b) {
    return (col){(int)a, (int)b};
}
"""

    ast: ClangAST = ClangAST("test.c", source_code)
    gen: ESBMCCodeGenerator = ESBMCCodeGenerator(ast)

    fns = ast.get_fn_decl()
