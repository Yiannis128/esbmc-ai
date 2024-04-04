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
    assert (
        SolutionGenerator.get_code_from_solution("This is a code block:```abc\n```")
        == "This is a code block:```abc\n```"
    )
