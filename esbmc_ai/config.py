# Author: Yiannis Charalambous 2023

import os
import json
import sys
from platform import system as system_name
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

from typing import Any, NamedTuple, Optional, Union, Sequence
from dataclasses import dataclass
from langchain.schema import BaseMessage

from esbmc_ai.logging import printv, set_verbose
from .ai_models import *
from .api_key_collection import APIKeyCollection
from .chat_response import json_to_base_messages


api_keys: APIKeyCollection

esbmc_path: str = "~/.local/bin/esbmc"
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
ai_model: AIModel = AIModels.GPT_3.value

esbmc_output_type: str = "full"
source_code_format: str = "full"

fix_code_max_attempts: int = 5

requests_max_tries: int = 5
requests_timeout: float = 60
verifier_timeout: float = 60

loading_hints: bool = False
allow_successful: bool = False
# Show the raw conversation after the command ends
raw_conversation: bool = False

cfg_path: str


class AIAgentConversation(NamedTuple):
    """Immutable class describing the conversation definition for an AI agent. The
    class represents the system messages of the AI agent defined and contains a load
    class method for efficiently loading it from config."""

    messages: tuple[BaseMessage, ...]

    @classmethod
    def from_seq(cls, message_list: Sequence[BaseMessage]) -> "AIAgentConversation":
        return cls(messages=tuple(message_list))

    @classmethod
    def load_from_config(
        cls, messages_list: list[dict[str, str]]
    ) -> "AIAgentConversation":
        return cls(messages=tuple(json_to_base_messages(messages_list)))


@dataclass
class ChatPromptSettings:
    """Settings for the AI Model. These settings act as an actor/agent, allowing the
    AI model to be applied into a specific scenario."""

    system_messages: AIAgentConversation
    """The generic prompt system messages of the AI. Generic meaning it is used in
    every scenario, as opposed to dynamic system message. The value is a list of
    converstaions."""
    initial_prompt: str
    """The generic initial prompt to use for the agent."""
    temperature: float


@dataclass
class DynamicAIModelAgent(ChatPromptSettings):
    """Extension of the ChatPromptSettings to include dynamic"""

    scenarios: dict[str, AIAgentConversation]
    """Scenarios dictionary that contains system messages for different errors that
    ESBMC can give. More information can be found in the
    [wiki](https://github.com/Yiannis128/esbmc-ai/wiki/Configuration#dynamic-prompts). 
    Reads from the config file the following hierarchy:
    * Dictionary mapping of error type to dictionary. Accepts the following entries:
      * `system` mapping to an array. The array contains the conversation for the
      system message for this particular error."""

    @classmethod
    def to_chat_prompt_settings(
        cls, ai_model_agent: "DynamicAIModelAgent", scenario: str
    ) -> ChatPromptSettings:
        """DynamicAIModelAgent extensions are not used by BaseChatInterface derived classes
        directly, since they only use the SystemMessages of ChatPromptSettings. This applies
        the correct scenario as a System Message and returns a pure ChatPromptSettings object
        for use. **Will return a shallow copy even if the system message is to be used**.
        """
        if scenario in ai_model_agent.scenarios:
            return ChatPromptSettings(
                initial_prompt=ai_model_agent.initial_prompt,
                system_messages=ai_model_agent.scenarios[scenario],
                temperature=ai_model_agent.temperature,
            )
        else:
            return ChatPromptSettings(
                initial_prompt=ai_model_agent.initial_prompt,
                system_messages=ai_model_agent.system_messages,
                temperature=ai_model_agent.temperature,
            )


chat_prompt_user_mode: DynamicAIModelAgent
chat_prompt_generator_mode: DynamicAIModelAgent
chat_prompt_optimize_code: ChatPromptSettings

esbmc_params_optimize_code: list[str] = [
    "--incremental-bmc",
    "--no-bounds-check",
    "--no-pointer-check",
    "--no-div-by-zero-check",
]


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


def load_envs() -> None:
    """Environment variables are loaded in the following order:

    1. Environment variables already loaded. Any variable not present will be looked for in
    .env files in the following locations.
    2. .env file in the current directory, moving upwards in the directory tree.
    3. esbmc-ai.env file in the current directory, moving upwards in the directory tree.
    4. esbmc-ai.env file in $HOME/.config/ for Linux/macOS and %userprofile% for Windows.

    Note: ESBMC_AI_CFG_PATH undergoes tilde user expansion and also environment
    variable expansion.
    """

    def get_env_vars() -> None:
        """Gets all the system environment variables that are currently loaded."""
        for k in keys:
            value: Optional[str] = os.getenv(k)
            if value != None:
                values[k] = value

    keys: list[str] = ["OPENAI_API_KEY", "HUGGINGFACE_API_KEY", "ESBMC_AI_CFG_PATH"]
    values: dict[str, str] = {}

    # Load from system env
    get_env_vars()

    # Find .env in current working directory and load it.
    dotenv_file_path: str = find_dotenv(usecwd=True)
    if dotenv_file_path != "":
        load_dotenv(dotenv_path=dotenv_file_path, override=False, verbose=True)
    else:
        # Find esbmc-ai.env in current working directory and load it.
        dotenv_file_path: str = find_dotenv(filename="esbmc-ai.env", usecwd=True)
        if dotenv_file_path != "":
            load_dotenv(dotenv_path=dotenv_file_path, override=False, verbose=True)

    get_env_vars()

    # Look for .env in home folder.
    home_path: Path = Path.home()
    match system_name():
        case "Linux" | "Darwin":
            home_path /= ".config/esbmc-ai.env"
        case "Windows":
            home_path /= "esbmc-ai.env"
        case _:
            raise ValueError(f"Unknown OS type: {system_name()}")

    load_dotenv(home_path, override=False, verbose=True)

    get_env_vars()

    # Check if all the values are set, else error.
    for key in keys:
        if key not in values:
            print(f"Error: No ${key} in environment.")
            sys.exit(1)

    global api_keys
    api_keys = APIKeyCollection(
        openai=str(os.getenv("OPENAI_API_KEY")),
        huggingface=str(os.getenv("HUGGINGFACE_API_KEY")),
    )

    global cfg_path
    cfg_path = os.path.expanduser(
        os.path.expandvars(str(os.getenv("ESBMC_AI_CFG_PATH")))
    )


def _load_ai_data(config: dict) -> None:
    # User chat mode will store extra AIAgentConversations into scenarios.
    global chat_prompt_user_mode
    chat_prompt_user_mode = DynamicAIModelAgent(
        system_messages=AIAgentConversation.load_from_config(
            config["chat_modes"]["user_chat"]["system"]
        ),
        initial_prompt=config["chat_modes"]["user_chat"]["initial"],
        temperature=config["chat_modes"]["user_chat"]["temperature"],
        scenarios={
            "set_solution": AIAgentConversation.load_from_config(
                messages_list=config["chat_modes"]["user_chat"]["set_solution"],
            ),
        },
    )

    # Generator mode loads scenarios normally.
    json_fcm_scenarios: dict = config["chat_modes"]["generate_solution"]["scenarios"]
    fcm_scenarios: dict = {
        scenario: AIAgentConversation.load_from_config(messages["system"])
        for scenario, messages in json_fcm_scenarios.items()
    }
    global chat_prompt_generator_mode
    chat_prompt_generator_mode = DynamicAIModelAgent(
        system_messages=AIAgentConversation.load_from_config(
            config["chat_modes"]["generate_solution"]["system"]
        ),
        initial_prompt=config["chat_modes"]["generate_solution"]["initial"],
        temperature=config["chat_modes"]["generate_solution"]["temperature"],
        scenarios=fcm_scenarios,
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
    if not os.path.exists(file_path) and os.path.isfile(file_path):
        print(f"Error: Config not found: {file_path}")
        sys.exit(1)

    config_file = None
    with open(file_path, mode="r") as file:
        config_file = json.load(file)

    global esbmc_params
    esbmc_params, _ = _load_config_value(
        config_file,
        "esbmc_params",
        esbmc_params,
    )

    global fix_code_max_attempts
    fix_code_max_attempts = int(
        _load_config_real_number(
            config_file=config_file["chat_modes"]["generate_solution"],
            name="max_attempts",
            default=fix_code_max_attempts,
        )
    )

    global source_code_format
    source_code_format, _ = _load_config_value(
        config_file=config_file,
        name="source_code_format",
        default=source_code_format,
    )

    if source_code_format not in ["full", "single"]:
        raise Exception(
            f"Source code format in the config is not valid: {source_code_format}"
        )

    global esbmc_output_type
    esbmc_output_type, _ = _load_config_value(
        config_file=config_file,
        name="esbmc_output_type",
        default=esbmc_output_type,
    )

    if esbmc_output_type not in ["full", "vp", "ce"]:
        raise Exception(
            f"ESBMC output type in the config is not valid: {esbmc_output_type}"
        )

    global requests_max_tries
    requests_max_tries = int(
        _load_config_real_number(
            config_file=config_file["llm_requests"],
            name="max_tries",
            default=requests_max_tries,
        )
    )

    global requests_timeout
    requests_timeout = _load_config_real_number(
        config_file=config_file["llm_requests"],
        name="timeout",
        default=requests_timeout,
    )

    global verifier_timeout
    verifier_timeout = _load_config_real_number(
        config_file=config_file,
        name="verifier_timeout",
        default=verifier_timeout,
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
    # Expand variables and tilde.
    esbmc_path = os.path.expanduser(os.path.expandvars(esbmc_path))

    # Load the AI data from the file that will command the AI for all modes.
    printv("Initializing AI data")
    _load_ai_data(config=config_file)


def load_args(args) -> None:
    set_verbose(args.verbose)

    global ai_model
    if args.ai_model != "":
        if is_valid_ai_model(args.ai_model):
            ai_model = get_ai_model_by_name(args.ai_model)
        else:
            print(f"Error: invalid --ai-model parameter {args.ai_model}")
            sys.exit(4)

    global raw_conversation
    raw_conversation = args.raw_conversation

    global esbmc_params
    # If append flag is set, then append.
    if args.append:
        esbmc_params.extend(args.remaining)
    elif len(args.remaining) != 0:
        esbmc_params = args.remaining
