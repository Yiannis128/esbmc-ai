#!/usr/bin/env python3

# Author: Yiannis Charalambous 2023

import os
import re
import sys
from time import sleep

# Enables arrow key functionality for input(). Do not remove import.
import readline

import argparse
from langchain.base_language import BaseLanguageModel

import esbmc_ai_lib.config as config
from esbmc_ai_lib.frontend.solution import (
    SourceFile,
    get_main_source_file,
    set_main_source_file,
    get_main_source_file_path,
)

from esbmc_ai_lib.commands import (
    ChatCommand,
    FixCodeCommand,
    HelpCommand,
    ExitCommand,
    OptimizeCodeCommand,
)

from esbmc_ai_lib import version
from esbmc_ai_lib.term import get_terminal_width
from esbmc_ai_lib.loading_widget import LoadingWidget, create_loading_widget
from esbmc_ai_lib.user_chat import UserChat
from esbmc_ai_lib.logging import printv, printvv
from esbmc_ai_lib.esbmc_util import esbmc
from esbmc_ai_lib.chat_response import FinishReason, json_to_base_messages, ChatResponse
from esbmc_ai_lib.ai_models import _ai_model_names


commands: list[ChatCommand] = []
command_names: list[str]
help_command: HelpCommand = HelpCommand()
fix_code_command: FixCodeCommand = FixCodeCommand()
optimize_code_command: OptimizeCodeCommand = OptimizeCodeCommand()
# verify_code_command: VerifyCodeCommand = VerifyCodeCommand()
exit_command: ExitCommand = ExitCommand()

chat: UserChat

AUTHORS: list[str] = ["Yiannis Charalambous"]

PROLOGUE: str = f"ESBMC-AI\nMade by {', '.join(AUTHORS)}"

HELP_MESSAGE: str = f"""{PROLOGUE}

Tool that passes ESBMC output into an LLM and allows for natural language
explanations among other things. Type /help in order to view available commands."""

ESBMC_HELP: str = """Additional ESBMC Arguments - The following are useful
arguments that can be added after the filename to modify ESBMC functionality.
Use the -a or --append parameter to append the options to the ones defined in the
config. 

For all the options, run ESBMC with -h as a parameter:

  --compact-trace                  add trace information to output
  --no-assertions                  ignore assertions
  --no-bounds-check                do not do array bounds check
  --no-div-by-zero-check           do not do division by zero check
  --no-pointer-check               do not do pointer check
  --no-align-check                 do not check pointer alignment
  --no-pointer-relation-check      do not check pointer relations
  --no-unlimited-scanf-check       do not do overflow check for scanf/fscanf
                                   with unlimited character width.
  --nan-check                      check floating-point for NaN
  --memory-leak-check              enable memory leak check
  --overflow-check                 enable arithmetic over- and underflow check
  --ub-shift-check                 enable undefined behaviour check on shift
                                   operations
  --struct-fields-check            enable over-sized read checks for struct
                                   fields
  --deadlock-check                 enable global and local deadlock check with
                                   mutex
  --data-races-check               enable data races check
  --lock-order-check               enable for lock acquisition ordering check
  --atomicity-check                enable atomicity check at visible
                                   assignments
  --stack-limit bits (=-1)         check if stack limit is respected
  --error-label label              check if label is unreachable
  --force-malloc-success           do not check for malloc/new failure
"""


def check_health() -> None:
    printv("Performing health check...")
    # Check that ESBMC exists.
    if os.path.exists(config.esbmc_path):
        printv("ESBMC has been located")
    else:
        print(f"Error: ESBMC could not be found in {config.esbmc_path}")
        sys.exit(3)


def print_assistant_response(
    chat: UserChat,
    response: ChatResponse,
    hide_stats: bool = False,
) -> None:
    print(f"{response.message.type}: {response.message.content}\n\n")

    if not hide_stats:
        print(
            "Stats:",
            f"total tokens: {response.total_tokens},",
            f"max tokens: {chat.ai_model.tokens}",
            f"finish reason: {response.finish_reason}",
        )


def init_commands_list() -> None:
    # Setup Help command and commands list.
    global help_command
    commands.extend(
        [
            help_command,
            exit_command,
            fix_code_command,
            optimize_code_command,
            # verify_code_command,
        ]
    )
    help_command.set_commands(commands)

    global command_names
    command_names = [command.command_name for command in commands]


def update_solution(source_code: str) -> None:
    set_main_source_file(SourceFile(get_main_source_file_path(), source_code))


def init_commands() -> None:
    """# Bus Signals
    Function that handles initializing commands. Each command needs to be added
    into the commands array in order for the command to register to be called by
    the user and also register in the help system."""

    # Let the AI model know about the corrected code.
    fix_code_command.on_solution_signal.add_listener(chat.set_solution)
    fix_code_command.on_solution_signal.add_listener(update_solution)

    optimize_code_command.on_solution_signal.add_listener(chat.set_solution)
    optimize_code_command.on_solution_signal.add_listener(update_solution)


def _run_command_mode(
    command: ChatCommand,
    args: str,
    esbmc_output: str,
    source_code: str,
) -> None:
    if command == fix_code_command:
        error, solution = fix_code_command.execute(
            file_name=get_main_source_file_path(),
            source_code=source_code,
            esbmc_output=esbmc_output,
            max_retries=config.fix_code_max_attempts,
        )

        if error:
            print("Failed all attempts...")
            sys.exit(1)
        else:
            print(solution)
    elif command == optimize_code_command:
        function_names: list[str] = args.split(",")
        error, solution = optimize_code_command.execute(
            file_path=get_main_source_file_path(),
            source_code=source_code,
            function_names=function_names if len(args) > 0 else [],
        )

        print(solution)
        sys.exit(1 if error else 0)
    else:
        command.execute()
    sys.exit(0)


def parse_command(user_prompt_string: str) -> tuple[str, list[str]]:
    """Parses a command and returns it based on the command rules outlined in
    the wiki: https://github.com/Yiannis128/esbmc-ai/wiki/User-Chat-Mode"""
    regex_pattern: str = (
        r'\s+(?=(?:[^\\"]*(?:\\.[^\\"]*)*)$)|(?:(?<!\\)".*?(?<!\\)")|(?:\\.)+|\S+'
    )
    segments: list[str] = re.findall(regex_pattern, user_prompt_string)
    parsed_array: list[str] = [segment for segment in segments if segment != " "]
    # Remove all empty spaces.
    command: str = parsed_array[0]
    command_args: list[str] = parsed_array[1:]
    return command, command_args


def main() -> None:
    init_commands_list()

    parser = argparse.ArgumentParser(
        # prog="ESBMC-AI",
        description=HELP_MESSAGE,
        # argparse.RawDescriptionHelpFormatter allows the ESBMC_HELP to display properly.
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="GitHub: https://github.com/Yiannis128/esbmc-ai",
    )

    parser.add_argument(
        "filename",
        help="The filename to pass to esbmc.",
    )

    parser.add_argument(
        "remaining",
        nargs=argparse.REMAINDER,
        help="Any arguments after the filename will be passed to ESBMC as parameters. Any ESBMC-AI parameters will need to be included before the filename.",
    )

    parser.add_argument(
        "-e",
        "--env",
        default=None,
        help="Override the default .env file location, which is in the current working directory.",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Show up to 3 levels of verbose output. Level 1: extra information. Level 2: show failed generations, show ESBMC output. Level 3: print hidden pushes to the message stack.",
    )

    parser.add_argument(
        "-m",
        "--ai-model",
        default="",
        help="Which AI model to use. Built-in models: {"
        + ", ".join(_ai_model_names)
        + ", +custom models}",
    )

    parser.add_argument(
        "-a",
        "--append",
        action="store_true",
        default=False,
        help="Any ESBMC parameters passed after the file name will be appended to the ones set in the config file, or the default ones if config file options are not set.",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"ESBMC-AI v{version}",
    )

    command_mode_parser = parser.add_argument_group(
        title="Command Mode",
        description="Run the program in command mode, this will skip User Chat Mode and automatically run a command. The program will exit after the command ends with an exit code.",
    )

    command_mode_parser.add_argument(
        "-c",
        "--command",
        choices=command_names,
        metavar="",
        help="Specify the command to run. Options: {" + ", ".join(command_names) + "}",
    )

    command_mode_parser.add_argument(
        "-p",
        "--params",
        default="",
        help="Arguments for the current command, supplied using the -c or --command parameter.",
    )

    parser.add_argument_group(
        title="ESBMC",
        description=ESBMC_HELP,
    )

    args = parser.parse_args()

    print(PROLOGUE)
    print()

    config.load_envs(args.env)
    config.load_config(config.cfg_path)
    config.load_args(args)

    check_health()

    anim: LoadingWidget = create_loading_widget()

    # Read the source code and esbmc output.
    printv("Reading source code...")
    print(f"Running ESBMC with {config.esbmc_params}\n")

    # Cast to string (for language servers)
    args.filename = str(args.filename)

    # Read source code
    with open(args.filename, mode="r") as file:
        # Add the main source file to the solution explorer.
        set_main_source_file(SourceFile(args.filename, file.read()))

    anim.start("ESBMC is processing... Please Wait")
    exit_code, esbmc_output, esbmc_err_output = esbmc(
        path=get_main_source_file_path(),
        esbmc_params=config.esbmc_params,
    )
    anim.stop()

    # Print verbose lvl 2
    printvv("-" * get_terminal_width())
    printvv(esbmc_output)
    printvv(esbmc_err_output)
    printvv("-" * get_terminal_width())

    # ESBMC will output 0 for verification success and 1 for verification
    # failed, if anything else gets thrown, it's an ESBMC error.
    if not config.allow_successful and exit_code == 0:
        print("Success!")
        print(esbmc_output)
        sys.exit(0)
    elif exit_code != 0 and exit_code != 1:
        print(f"ESBMC exit code: {exit_code}")
        print(f"ESBMC Output:\n\n{esbmc_err_output}")
        sys.exit(1)

    # Command mode: Check if command is called and call it.
    # If not, then continue to user mode.
    if args.command != None:
        command = args.command
        if command in command_names:
            print("Running Command:", command)
            for idx, command_name in enumerate(command_names):
                if command == command_name:
                    _run_command_mode(
                        command=commands[idx],
                        args=args.params,
                        source_code=get_main_source_file().content,
                        esbmc_output=esbmc_output,
                    )
            sys.exit(0)

    printv(f"Initializing the LLM: {config.ai_model.name}\n")
    chat_llm: BaseLanguageModel = config.ai_model.create_llm(
        api_keys=config.api_keys,
        temperature=config.chat_prompt_user_mode.temperature,
    )

    printv("Creating user chat")
    global chat
    chat = UserChat(
        system_messages=json_to_base_messages(
            config.chat_prompt_user_mode.system_messages
        ),
        ai_model=config.ai_model,
        llm=chat_llm,
        source_code=get_main_source_file().content,
        esbmc_output=esbmc_output,
    )

    printv("Initializing commands...")
    init_commands()

    # Show the initial output.
    response: ChatResponse
    if len(config.chat_prompt_user_mode.initial_prompt) > 0:
        printv("Using initial prompt from file...\n")
        anim.start("Model is parsing ESBMC output... Please Wait")
        response = chat.send_message(
            message=config.chat_prompt_user_mode.initial_prompt,
            protected=True,
        )
        anim.stop()

        if response.finish_reason == FinishReason.length:
            raise RuntimeError(f"The token length is too large: {chat.ai_model.tokens}")
    else:
        raise RuntimeError("User mode initial prompt not found in config.")

    print_assistant_response(chat, response)
    print(
        "ESBMC-AI: Type '/help' to view the available in-chat commands, along",
        "with useful prompts to ask the AI model...",
    )

    while True:
        # Get user input.
        user_message = input("user>: ")

        # Check if it is a command, if not, then pass it to the chat interface.
        if user_message.startswith("/"):
            command, command_args = parse_command(user_message)
            command = command[1:]  # Remove the /
            if command == fix_code_command.command_name:
                # Fix Code command
                print()
                print("ESBMC-AI will generate a fix for the code...")

                error, solution = fix_code_command.execute(
                    file_name=get_main_source_file_path(),
                    source_code=get_main_source_file().content,
                    esbmc_output=esbmc_output,
                    max_retries=config.fix_code_max_attempts,
                )

                if not error:
                    print(
                        "\n\nassistant: Here is the corrected code, verified with ESBMC:"
                    )
                    print(f"```\n{solution}\n```")
                continue
            elif command == optimize_code_command.command_name:
                # Optimize Code command
                error, solution = optimize_code_command.execute(
                    file_path=get_main_source_file_path(),
                    source_code=get_main_source_file().content,
                    function_names=command_args,
                )

                if error:
                    # Print error
                    print("\n" + solution + "\n")
                else:
                    print(f"\nOptimizations Completed:\n```c\n{solution}```\n")

                continue
            else:
                # Commands without parameters or returns are handled automatically.
                found: bool = False
                for cmd in commands:
                    if cmd.command_name == command:
                        found = True
                        cmd.execute()
                        break

                if not found:
                    print("Error: Unknown command...")
                continue
        elif user_message == "":
            continue
        else:
            print()

        # User chat mode send and process current message response.
        while True:
            # Send user message to AI model and process.
            anim.start("Generating response... Please Wait")
            response = chat.send_message(user_message)
            anim.stop()
            if response.finish_reason == FinishReason.stop:
                break
            elif response.finish_reason == FinishReason.length:
                anim.start(
                    "Message stack limit reached. Shortening message stack... Please Wait"
                )
                sleep(config.consecutive_prompt_delay)
                chat.compress_message_stack()
                sleep(config.consecutive_prompt_delay)
                anim.stop()
                continue
            else:
                raise NotImplementedError(
                    f"User Chat Mode: Finish Reason: {response.finish_reason}"
                )

        print_assistant_response(
            chat,
            response,
        )


if __name__ == "__main__":
    main()
