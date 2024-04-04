# Author: Yiannis Charalambous

from esbmc_ai.solution_generator import SolutionGenerator


def test_get_code_from_solution():
    assert (
        SolutionGenerator.get_code_from_solution(
            "This is a code block:\n\n```c\naaa\n```"
        )
        == "aaa"
    )

    assert (
        SolutionGenerator.get_code_from_solution(
            "This is a code block:\n\n```\nabc\n```"
        )
        == "abc"
    )

    # Edge case
    assert (
        SolutionGenerator.get_code_from_solution("This is a code block:```abc\n```")
        == ""
    )

    assert (
        SolutionGenerator.get_code_from_solution("The repaired C code is:\n\n```\n```")
        == ""
    )
