# Author: Yiannis Charalambous 2023

from pytest import raises

import esbmc_ai_lib.config as config

from esbmc_ai_lib.ai_models import is_valid_ai_model


def test_load_config_value() -> None:
    result, ok = config._load_config_value(
        {
            "test": "value",
        },
        "test",
    )
    assert ok and result == "value"


def test_load_config_value_default_value() -> None:
    result, ok = config._load_config_value(
        {
            "test": "value",
        },
        "test",
        "wrong",
    )
    assert ok and result == "value"


def test_load_config_value_default_value_not_exists() -> None:
    result, ok = config._load_config_value(
        {},
        "test2",
        "wrong",
    )
    assert not ok and result == "wrong"


def test_load_config_real_number() -> None:
    result = config._load_config_real_number(
        {
            "test": 1.0,
        },
        "test",
    )
    assert result == 1.0


def test_load_config_real_number_default_value() -> None:
    result = config._load_config_real_number({}, "test", 1.1)
    assert result == 1.1


def test_load_config_real_number_wrong_value() -> None:
    with raises(TypeError):
        result = config._load_config_real_number(
            {
                "test": "wrong value",
            },
            "test",
        )
        assert result == None


def test_load_config_real_number_wrong_value_default() -> None:
    with raises(TypeError):
        result = config._load_config_real_number(
            {
                "test": "wrong value",
            },
            "test",
            1.0,
        )
        assert result == None


def test_load_custom_ai() -> None:
    custom_ai_config: dict = {
        "example_ai": {
            "max_tokens": 4096,
            "url": "www.example.com",
            "config_message": {
                "template": "example",
                "system": "{content}",
                "ai": "{content}",
                "human": "{content}",
            },
        }
    }

    config._load_custom_ai(custom_ai_config)

    assert is_valid_ai_model("example_ai")


def test_load_custom_ai_fail() -> None:
    # Wrong max_tokens type
    ai_conf: dict = {
        "example_ai_2": {
            "max_tokens": "1024",
            "url": "www.example.com",
            "config_message": "example",
        }
    }

    with raises(AssertionError):
        config._load_custom_ai(ai_conf)

    # Wrong max_tokens value
    ai_conf: dict = {
        "example_ai_2": {
            "max_tokens": 0,
            "url": "www.example.com",
            "config_message": "example",
        }
    }

    with raises(AssertionError):
        config._load_custom_ai(ai_conf)

    # Missing max_tokens
    ai_conf: dict = {
        "example_ai_2": {
            "url": "www.example.com",
            "config_message": "example",
        }
    }

    with raises(AssertionError):
        config._load_custom_ai(ai_conf)

    # Missing url
    ai_conf: dict = {
        "example_ai_2": {
            "max_tokens": 0,
            "config_message": "example",
        }
    }

    with raises(AssertionError):
        config._load_custom_ai(ai_conf)

    # Missing config message
    ai_conf: dict = {
        "example_ai_2": {
            "max_tokens": 0,
            "url": "www.example.com",
        }
    }

    with raises(AssertionError):
        config._load_custom_ai(ai_conf)

    # Test load empty
    ai_conf: dict = {}

    config._load_custom_ai(ai_conf)
