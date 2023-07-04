from esbmc_ai_lib.__main__ import parse_command


def test_parse() -> None:
    sentence = 'Your sentence goes "here and \\"here\\" as well."'
    result = parse_command(sentence)
    assert result == (
        "Your",
        [
            "sentence",
            "goes",
            '"here and \\"here\\" as well."',
        ],
    )


def test_parse_command() -> None:
    result = parse_command("/fix-code")
    assert result == ("/fix-code", [])


def test_parse_command_args() -> None:
    result = parse_command("/optimize-code main")
    assert result == ("/optimize-code", ["main"])
