# Author: Yiannis Charalambous 2023

import esbmc_ai_lib.frontend.ast as ast
from esbmc_ai_lib.frontend.ast import ClangAST, FunctionDeclaration, Declaration
from esbmc_ai_lib.frontend.ast_decl import InclusionDirective, TypeDeclaration


def test_get_source_code() -> None:
    fn_atomic_acquire = """void __VERIFIER_atomic_acquire(void)
{
    __VERIFIER_assume(a == 0);
    a = 1;
}"""
    fn_c = """void *c(void *arg)
{
    ;
    __VERIFIER_atomic_acquire();
    b = 1;
    return NULL;
}"""
    fn_main = """int main()
{
    pthread_create(&d, 0, c, 0);
    __VERIFIER_atomic_acquire();
    if (!b)
        assert(0);
    return 0;
}"""
    source_code = f"""#include <pthread.h>
#include <assert.h>

int a, b;
{fn_atomic_acquire}
{fn_c}
pthread_t d;
{fn_main}"""
    ast: ClangAST = ClangAST("test.c", source_code=source_code)

    fns: list[FunctionDeclaration] = ast.get_fn_decl()

    assert ast.get_source_code(fns[0]) == fn_atomic_acquire
    assert ast.get_source_code(fns[1]) == fn_c
    assert ast.get_source_code(fns[2]) == fn_main


def test_ast_functions() -> None:
    file = "test.c"
    source_code = """#include <pthread.h>
#include <assert.h>

int a, b;
void __VERIFIER_atomic_acquire(void)
{
    __VERIFIER_assume(a == 0);
    a = 1;
}
void *c(void *arg)
{
    ;
    __VERIFIER_atomic_acquire();
    b = 1;
    return NULL;
}
pthread_t d;
int main()
{
    pthread_create(&d, 0, c, 0);
    __VERIFIER_atomic_acquire();
    if (!b)
        assert(0);
    return 0;
}"""
    cast = ast.ClangAST(file_path=file, source_code=source_code)
    functions: list[FunctionDeclaration] = cast.get_fn_decl()
    answer: list[FunctionDeclaration] = [
        FunctionDeclaration(
            name="__VERIFIER_atomic_acquire",
            type_name="void",
            args=[],
        ),
        FunctionDeclaration(
            name="c",
            type_name="void *",
            args=[Declaration(name="arg", type_name="void *")],
        ),
        FunctionDeclaration(
            name="main",
            type_name="int",
            args=[],
        ),
    ]

    assert functions[0] == answer[0]
    assert functions[1] == answer[1]
    assert functions[2] == answer[2]


def test_ast_functions_blank() -> None:
    file = "test.c"
    source_code = """#include <pthread.h>
#include <assert.h>
int a, b;
pthread_t d;
    """

    cast = ast.ClangAST(file_path=file, source_code=source_code)
    functions: list[FunctionDeclaration] = cast.get_fn_decl()
    assert functions == []


def test_get_type_decl() -> None:
    source_code = """struct linear
{
    int value;
};

typedef struct linear LinearTypeDef;

typedef struct
{
    int x;
    int y;
} Point;

Point a;
Point *b;

int c;

char *d;

typedef enum Types
{
    ONE,
    TWO,
    THREE
} Typest;

enum Types e = ONE;

Typest f = TWO;

union Combines
{
    int a;
    int b;
    int c;
};

typedef union Combines CombinesTypeDef;

enum extra { A, B, C};

typedef enum extra ExtraEnum;"""

    ast: ClangAST = ClangAST("test.c", source_code)
    types: list[TypeDeclaration] = ast.get_type_decl()
    types_str: list[str] = [str(t) for t in types]

    assert types_str[0] == "struct linear {value: int}"
    assert (
        types_str[1]
        == "typedef (LinearTypeDef) struct linear {struct linear: struct linear}"
    )
    assert types_str[2] == "Point {x: int, y: int}"
    assert types_str[3] == "typedef (Point) Point {Point: Point}"
    assert types_str[4] == "enum Types {ONE: int, TWO: int, THREE: int}"
    assert types_str[5] == "typedef (Typest) enum Types {Types: enum Types}"
    assert types_str[6] == "union Combines {a: int, b: int, c: int}"
    assert types_str[6] == "union Combines {a: int, b: int, c: int}"
    assert (
        types_str[7]
        == "typedef (CombinesTypeDef) union Combines {union Combines: union Combines}"
    )


def test_get_variable_decl() -> None:
    source_code: str = """int a, b;
char* c;
char d[10];
int e = 100;
float f = 0.1f;"""

    ast: ClangAST = ClangAST("test.c", source_code)
    vars: list[str] = [str(var) for var in ast.get_variable_decl()]

    assert vars[0] == "a:int"
    assert vars[1] == "b:int"
    assert vars[2] == "c:char *"
    assert vars[3] == "d:char[10]"
    assert vars[4] == "e:int"
    assert vars[5] == "f:float"


def test_get_include_directives() -> None:
    source_code: str = """#include <assert.h>
#include <stdlib.h>"""

    ast: ClangAST = ClangAST("test.c", source_code)
    includes: list[InclusionDirective] = ast.get_include_directives()
    includes[0].path = "assert.h"
    includes[1].path = "stdlib.h"

    assert str(includes[0]) == '#include "assert.h"'
    assert str(includes[1]) == '#include "stdlib.h"'
