# Author: Yiannis Charalambous 2023

import pytest

import esbmc_ai_lib.frontend.ast as ast


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
}
    """
    cast = ast.ClangAST(file_path=file, source_code=source_code)
    functions = set(cast.get_function_declarations())
    assert functions == set(
        [
            "__VERIFIER_atomic_acquire",
            "c",
            "main",
        ],
    )


def test_ast_functions_blank() -> None:
    file = "test.c"
    source_code = """#include <pthread.h>
#include <assert.h>
int a, b;
pthread_t d;
    """

    cast = ast.ClangAST(file_path=file, source_code=source_code)
    functions = cast.get_function_declarations()
    assert functions == []
