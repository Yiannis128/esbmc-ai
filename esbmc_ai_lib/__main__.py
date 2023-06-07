#!/usr/bin/env python3

# Author: Yiannis Charalambous 2023

import os
from time import sleep

# Enables arrow key functionality for input(). Do not remove import.
import readline

import argparse
from typing import Any
import openai

import esbmc_ai_lib.config as config

from esbmc_ai_lib.commands import (
    ChatCommand,
    FixCodeCommand,
    HelpCommand,
    ExitCommand,
    VerifyCodeCommand,
)

from esbmc_ai_lib.loading_widget import LoadingWidget
from esbmc_ai_lib.user_chat import ChatInterface, ConversationSummarizerChat
from esbmc_ai_lib.base_chat_interface import (
    ChatResponse,
    FINISH_REASON_LENGTH,
    FINISH_REASON_STOP,
)
from esbmc_ai_lib.logging import printv
from esbmc_ai_lib.esbmc_util import esbmc


commands: list[ChatCommand] = []
command_names: list[str]
help_command: HelpCommand = HelpCommand()
fix_code_command: FixCodeCommand = FixCodeCommand()
verify_code_command: VerifyCodeCommand = VerifyCodeCommand()
exit_command: ExitCommand = ExitCommand()

chat: ChatInterface

HELP_MESSAGE: str = """Tool that passes ESBMC output into ChatGPT and allows for natural language
explanations. Type /help in order to view available commands."""

ESBMC_HELP: str = """Additional ESBMC Arguments - The following are useful
arguments that can be added after the filename to modify ESBMC functionality.
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


def init_check_health(verbose: bool) -> None:
    def printv(m) -> None:
        if verbose:
            print(m)

    printv("Performing init health check...")
    # Check that the .env file exists.
    if os.path.exists(".env"):
        printv("Environment file has been located")
    else:
        print("Error: .env file is not found in project directory")
        exit(3)


def check_health() -> None:
    printv("Performing health check...")
    # Check that ESBMC exists.
    if os.path.exists(config.esbmc_path):
        printv("ESBMC has been located")
    else:
        print(f"Error: ESBMC could not be found in {config.esbmc_path}")
        exit(3)


def get_src(path: str) -> str:
    with open(path, mode="r") as file:
        content = file.read()
        return str(content)


def print_assistant_response(
    chat: ChatInterface,
    response: ChatResponse,
    raw_responses: bool = False,
    hide_stats: bool = False,
) -> None:
    if raw_responses:
        print(response.base_message)
        return

    print(f"{response.role}: {response.message}\n\n")

    if not hide_stats:
        print(
            "Stats:",
            f"total tokens: {response.total_tokens},",
            f"max tokens: {chat.max_tokens}",
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
            verify_code_command,
        ]
    )
    help_command.set_commands(commands)

    global command_names
    command_names = [command.command_name for command in commands]


def init_commands() -> None:
    """Function that handles initializing commands. Each command needs to be added
    into the commands array in order for the command to register to be called by
    the user and also register in the help system."""
    # Bus Signals:
    # fix_code_command.on_solution_signal.add_listener(chat.set_solution)
    # fix_code_command.on_solution_signal.add_listener(verify_code_command.set_solution)
    pass


def _run_command_mode(
    command: ChatCommand,
    args,
    esbmc_output: str,
    source_code: str,
) -> None:
    if command == fix_code_command:
        error, solution = fix_code_command.execute(
            file_name=args.filename,
            source_code=source_code,
            esbmc_output=esbmc_output,
        )

        if error:
            print("Failed all attempts...")
            exit(1)
        else:
            print(solution)
    elif command == verify_code_command:
        raise NotImplementedError()
    else:
        command.execute()
    exit(0)


def main() -> None:
    init_commands_list()

    parser = argparse.ArgumentParser(
        prog="ESBMC-ChatGPT",
        description=HELP_MESSAGE,
        # argparse.RawDescriptionHelpFormatter allows the ESBMC_HELP to display
        # properly.
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"Made by Yiannis Charalambous\n\n{ESBMC_HELP}",
    )

    parser.add_argument("filename", help="The filename to pass to esbmc.")
    parser.add_argument(
        "remaining",
        nargs=argparse.REMAINDER,
        help="Any arguments after the filename will be passed to ESBMC as parameters.",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help="Output will be verbose.",
    )

    parser.add_argument(
        "-r",
        "--raw-output",
        action="store_true",
        default=False,
        help="Responses from AI model will be shown raw.",
    )

    parser.add_argument(
        "-m",
        "--ai-model",
        default="",
        help="Which AI model to use.",
    )

    parser.add_argument(
        "-a",
        "--append",
        action="store_true",
        default=False,
        help="Any ESBMC parameters passed after the file name will be appended to the ones set in the config file, or the default ones if config file options are not set.",
    )

    parser.add_argument(
        "-c",
        "--command",
        choices=command_names,
        help="Runs the program in command mode, it will exit after the command ends with an exit code.",
    )

    args = parser.parse_args()

    print("ESBMC-AI")
    print("Made by Yiannis Charalambous")
    print()

    init_check_health(args.verbose)

    config.load_envs()
    config.load_config(config.cfg_path)
    config.load_args(args)

    check_health()

    anim: LoadingWidget = LoadingWidget()

    # Read the source code and esbmc output.
    printv("Reading source code...")
    print(f"Running ESBMC with {config.esbmc_params}\n")
    source_code: str = get_src(args.filename)

    anim.start("ESBMC is processing... Please Wait")
    exit_code, esbmc_output = esbmc(
        path=args.filename,
        esbmc_params=config.esbmc_params,
    )
    anim.stop()

    # ESBMC will output 0 for verification success and 1 for verification
    # failed, if anything else gets thrown, it's an ESBMC error.
    if exit_code == 0:
        print("Success!")
        print(esbmc_output)
        exit(0)
    elif exit_code != 1:
        print(f"ESBMC exit code: {exit_code}")
        exit(1)

    printv("Initializing OpenAI")
    openai.api_key = config.openai_api_key

    # Command mode: Check if command is called and call it.
    # If not, then continue to user mode.
    if args.command in command_names:
        print("Running Command:", args.command)
        for idx, command_name in enumerate(command_names):
            if args.command == command_name:
                _run_command_mode(
                    command=commands[idx],
                    args=args,
                    source_code=source_code,
                    esbmc_output=esbmc_output,
                )
        exit(0)

    printv("Creating user chat mode summarizer...")
    chat_summarizer: ConversationSummarizerChat = ConversationSummarizerChat(
        system_messages=config.chat_prompt_conversation_summarizer.system_messages,
        model=config.ai_model,
        temperature=config.chat_temperature,
    )

    printv("Creating user chat")
    global chat
    chat = ChatInterface(
        system_messages=config.chat_prompt_user_mode.system_messages,
        model=config.ai_model,
        temperature=config.chat_temperature,
        summarizer=chat_summarizer,
        source_code=source_code,
        esbmc_output=esbmc_output,
    )
    printv(f"Using AI Model: {chat.model_name}")

    # Show the initial output.
    response: ChatResponse
    if len(config.chat_prompt_user_mode.initial_prompt) > 0:
        printv("Using initial prompt from file...\n")
        anim.start("Model is parsing ESBMC output... Please Wait")
        response = chat.send_message(config.chat_prompt_user_mode.initial_prompt, True)
        anim.stop()
    else:
        raise RuntimeError("User mode initial prompt not found in config.")

    print_assistant_response(chat, response, config.raw_responses)
    print(
        "ESBMC-AI: Type '/help' to view the available in-chat commands, along",
        "with useful prompts to ask the AI model...",
    )

    printv("Initializing commands...")
    init_commands()

    while True:
        # Get user input.
        user_message = input("user>: ")

        # Check if it is a command, if not, then pass it to the chat interface.
        if user_message.startswith("/"):
            command: str = user_message[1:]
            if command == fix_code_command.command_name:
                print()
                print("ESBMC-AI will generate a fix for the code...")

                error, solution = fix_code_command.execute(
                    file_name=args.filename,
                    source_code=source_code,
                    esbmc_output=esbmc_output,
                )

                if not error:
                    print(
                        "\n\nassistant: Here is the corrected code, verified with ESBMC:"
                    )
                    print(f"```\n{solution}\n```")
                    # Let the AI model know about the corrected code.
                    printv("Informing Chat AI about correct code...")
                    chat.set_solution(solution)
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

        # User chat mode send message and process
        while True:
            # Send user message to AI model and process.
            anim.start("Generating response... Please Wait")
            response = chat.send_message(user_message)
            anim.stop()
            if response.finish_reason == FINISH_REASON_STOP:
                break
            elif response.finish_reason == FINISH_REASON_LENGTH:
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
            config.raw_responses,
        )


if __name__ == "__main__":
    main()
