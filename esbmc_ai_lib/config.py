# Author: Yiannis Charalambous 2023

import os
import json
import sys
from typing import Any, NamedTuple, Optional, Union, Literal
from dotenv import load_dotenv

from .logging import *
from .ai_models import *
from .api_key_collection import APIKeyCollection


api_keys: APIKeyCollection

esbmc_path: str = "./esbmc"
esbmc_params: list[str] = [
    "--interval-analysis",
    "--goto-unwind",
    "--unlimited-goto-unwind",
    "--k-induction",
    "--state-hashing",
    "--add-symex-value-sets",
    "--k-step",
    "2",
    "--floatbv",
    "--unlimited-k-steps",
    "--compact-trace",
    "--context-bound",
    "2",
]

temp_auto_clean: bool = True
temp_file_dir: str = "."
consecutive_prompt_delay: float = 20.0
ai_model: AIModel = AIModels.GPT_3.value

loading_hints: bool = False
allow_successful: bool = False

cfg_path: str = "./config.json"


class ChatPromptSettings(NamedTuple):
    system_messages: list
    initial_prompt: str
    temperature: float


chat_prompt_user_mode: ChatPromptSettings
chat_prompt_generator_mode: ChatPromptSettings
chat_prompt_optimize_code: ChatPromptSettings

esbmc_params_optimize_code: list[str] = [
    "--incremental-bmc",
    "--no-bounds-check",
    "--no-pointer-check",
    "--no-div-by-zero-check",
]

ocm_array_expansion: int
"""Used for allocating continuous memory. Arrays and pointers will be initialized using this."""
ocm_init_max_depth: int
"""Max depth that structs will be initialized into, afterwards initializes with NULL."""
ocm_partial_equivalence_check: Literal["basic", "deep"] = "basic"
"""Mode to check for partial equivalence on the return value."""
fix_code_max_attempts: int = 10
"""Max attempts to fix a code."""


def _load_custom_ai(config: dict) -> None:
    ai_custom: dict = config
    for name, ai_data in ai_custom.items():
        # Load the max tokens
        custom_ai_max_tokens, ok = _load_config_value(
            config_file=ai_data,
            name="max_tokens",
        )
        assert ok, f'max_tokens field not found in "ai_custom" entry "{name}".'
        assert (
            isinstance(custom_ai_max_tokens, int) and custom_ai_max_tokens > 0
        ), f'custom_ai_max_tokens in ai_custom entry "{name}" needs to be an int and greater than 0.'
        # Load the URL
        custom_ai_url, ok = _load_config_value(
            config_file=ai_data,
            name="url",
        )
        assert ok, f'url field not found in "ai_custom" entry "{name}".'
        stop_sequences, ok = _load_config_value(
            config_file=ai_data,
            name="stop_sequences",
        )
        # Load the config message
        config_message: dict[str, str] = ai_data["config_message"]
        template, ok = _load_config_value(
            config_file=config_message,
            name="template",
        )
        human, ok = _load_config_value(
            config_file=config_message,
            name="human",
        )
        ai, ok = _load_config_value(
            config_file=config_message,
            name="ai",
        )
        system, ok = _load_config_value(
            config_file=config_message,
            name="system",
        )

        # Add the custom AI.
        add_custom_ai_model(
            AIModelTextGen(
                name=name,
                tokens=custom_ai_max_tokens,
                url=custom_ai_url,
                config_message=template,
                ai_template=ai,
                human_template=human,
                system_template=system,
                stop_sequences=stop_sequences,
            )
        )


def load_envs(env_override: Optional[str]) -> None:
    env_file_path: str = env_override if env_override else "./.env"
    # Check that the .env file exists.
    if os.path.exists(env_file_path):
        printv("Environment file has been located")
    else:
        print("Error: .env file is not found in project directory")
        sys.exit(3)

    load_dotenv(
        dotenv_path=env_file_path,
        override=True,
        verbose=True,
    )

    global api_keys

    api_keys = APIKeyCollection(
        openai=str(os.getenv("OPENAI_API_KEY")),
        huggingface=str(os.getenv("HUGGINGFACE_API_KEY")),
    )

    global cfg_path
    value = os.getenv("ESBMC_AI_CFG_PATH")
    if value != None:
        if os.path.exists(value):
            cfg_path = str(value)
        else:
            print(f"Error: Invalid .env ESBMC_AI_CFG_PATH value: {value}")
            sys.exit(4)
    else:
        print(
            f"Warning: ESBMC_AI_CFG_PATH not found in .env file... Defaulting to {cfg_path}"
        )


def _load_config_value(
    config_file: dict, name: str, default: object = None
) -> tuple[Any, bool]:
    if name in config_file:
        return config_file[name], True
    else:
        print(f"Warning: {name} not found in config... Using default value: {default}")
        return default, False


def _load_config_bool(
    config_file: dict,
    name: str,
    default: bool = False,
) -> bool:
    value, _ = _load_config_value(config_file, name, default)
    if isinstance(value, bool):
        return value
    else:
        raise TypeError(
            f"Error: config invalid {name} value: {value} "
            + "Make sure it is a bool value."
        )


def _load_config_real_number(
    config_file: dict, name: str, default: object = None
) -> Union[int, float]:
    value, _ = _load_config_value(config_file, name, default)
    # Type check
    if type(value) is float or type(value) is int:
        return value
    else:
        raise TypeError(
            f"Error: config invalid {name} value: {value} "
            + "Make sure it is a float or int..."
        )


def load_config(file_path: str) -> None:
    if not os.path.exists(file_path):
        print(f"Error: Config not found: {file_path}")
        sys.exit(4)

    config_file = None
    with open(file_path, mode="r") as file:
        config_file = json.load(file)

    global esbmc_params
    esbmc_params, _ = _load_config_value(
        config_file,
        "esbmc_params",
        esbmc_params,
    )

    global consecutive_prompt_delay
    consecutive_prompt_delay = _load_config_real_number(
        config_file,
        "consecutive_prompt_delay",
        consecutive_prompt_delay,
    )

    global temp_auto_clean
    temp_auto_clean, _ = _load_config_value(
        config_file,
        "temp_auto_clean",
        temp_auto_clean,
    )

    global temp_file_dir
    temp_file_dir, _ = _load_config_value(
        config_file,
        "temp_file_dir",
        temp_file_dir,
    )

    global allow_successful
    allow_successful = _load_config_bool(
        config_file,
        "allow_successful",
        False,
    )

    global loading_hints
    loading_hints = _load_config_bool(
        config_file,
        "loading_hints",
        True,
    )

    global ocm_array_expansion
    ocm_array_expansion, _ = _load_config_value(
        config_file=config_file["chat_modes"]["optimize_code"],
        name="array_expansion",
        default=20,
    )

    global ocm_init_max_depth
    ocm_init_max_depth, _ = _load_config_value(
        config_file=config_file["chat_modes"]["optimize_code"],
        name="init_max_depth",
        default=10,
    )

    global ocm_partial_equivalence_check
    ocm_partial_equivalence_check, _ = _load_config_value(
        config_file=config_file["chat_modes"]["optimize_code"],
        name="partial_equivalence_check",
        default="basic",
    )

    global fix_code_max_attempts
    fix_code_max_attempts = int(
        _load_config_real_number(
            config_file=config_file["chat_modes"]["generate_solution"],
            name="max_attempts",
            default=10,
        )
    )

    # Load the custom ai configs.
    _load_custom_ai(config_file["ai_custom"])

    global ai_model
    ai_model_name, _ = _load_config_value(
        config_file,
        "ai_model",
        ai_model,
    )
    if is_valid_ai_model(ai_model_name):
        # Load the ai_model from loaded models.
        ai_model = get_ai_model_by_name(ai_model_name)
    else:
        print(f"Error: {ai_model_name} is not a valid AI model")
        sys.exit(4)

    global esbmc_path
    # Health check verifies this later in the init process.
    esbmc_path, _ = _load_config_value(
        config_file,
        "esbmc_path",
        esbmc_path,
    )

    # Load the AI data from the file that will command the AI for all modes.
    printv("Initializing AI data")
    global chat_prompt_user_mode
    chat_prompt_user_mode = ChatPromptSettings(
        system_messages=config_file["chat_modes"]["user_chat"]["system"],
        initial_prompt=config_file["chat_modes"]["user_chat"]["initial"],
        temperature=config_file["chat_modes"]["user_chat"]["temperature"],
    )

    global chat_prompt_generator_mode
    chat_prompt_generator_mode = ChatPromptSettings(
        system_messages=config_file["chat_modes"]["generate_solution"]["system"],
        initial_prompt=config_file["chat_modes"]["generate_solution"]["initial"],
        temperature=config_file["chat_modes"]["generate_solution"]["temperature"],
    )

    global chat_prompt_optimize_code
    chat_prompt_optimize_code = ChatPromptSettings(
        system_messages=config_file["chat_modes"]["optimize_code"]["system"],
        initial_prompt=config_file["chat_modes"]["optimize_code"]["initial"],
        temperature=config_file["chat_modes"]["optimize_code"]["temperature"],
    )

    global esbmc_params_optimize_code
    esbmc_params_optimize_code, _ = _load_config_value(
        config_file["chat_modes"]["optimize_code"],
        "esbmc_params",
        esbmc_params_optimize_code,
    )


def load_args(args) -> None:
    set_verbose(args.verbose)

    global ai_model
    if args.ai_model != "":
        if is_valid_ai_model(args.ai_model):
            ai_model = get_ai_model_by_name(args.ai_model)
        else:
            print(f"Error: invalid --ai-model parameter {args.ai_model}")
            sys.exit(4)

    global esbmc_params
    # If append flag is set, then append.
    if args.append:
        esbmc_params.extend(args.remaining)
    elif len(args.remaining) != 0:
        esbmc_params = args.remaining
