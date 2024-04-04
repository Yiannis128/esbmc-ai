# Author: Yiannis Charalambous

from os import get_terminal_size
from typing import Any, Tuple
from typing_extensions import override
from langchain.schema import AIMessage, HumanMessage

from esbmc_ai.chat_response import FinishReason

from .chat_command import ChatCommand
from .. import config
from ..msg_bus import Signal
from ..loading_widget import create_loading_widget
from ..esbmc_util import (
    esbmc_get_error_type,
    esbmc_load_source_code,
)
from ..solution_generator import SolutionGenerator, get_esbmc_output_formatted
from ..logging import print_horizontal_line, printv, printvv

# TODO Remove built in messages and move them to config.


class FixCodeCommand(ChatCommand):
    on_solution_signal: Signal = Signal()

    def __init__(self) -> None:
        super().__init__(
            command_name="fix-code",
            help_message="Generates a solution for this code, and reevaluates it with ESBMC.",
        )
        self.anim = create_loading_widget()

    @override
    def execute(self, **kwargs: Any) -> Tuple[bool, str]:
        def print_raw_conversation() -> None:
            print("Notice: Printing raw conversation...")
            all_messages = solution_generator._system_messages.copy()
            all_messages.extend(solution_generator.messages.copy())
            messages: list[str] = [f"{msg.type}: {msg.content}" for msg in all_messages]
            print("\n" + "\n\n".join(messages))
            print("Notice: End of conversation")

        file_name: str = kwargs["file_name"]
        source_code: str = kwargs["source_code"]
        esbmc_output: str = kwargs["esbmc_output"]

        # Parse the esbmc output here and determine what "Scenario" to use.
        scenario: str = esbmc_get_error_type(esbmc_output)

        printv(f"Scenario: {scenario}")
        printv(
            f"Using dynamic prompt..."
            if scenario in config.chat_prompt_generator_mode.scenarios
            else "Using generic prompt..."
        )

        solution_generator = SolutionGenerator(
            ai_model_agent=config.chat_prompt_generator_mode,
            source_code=source_code,
            esbmc_output=esbmc_output,
            ai_model=config.ai_model,
            llm=config.ai_model.create_llm(
                api_keys=config.api_keys,
                temperature=config.chat_prompt_generator_mode.temperature,
                requests_max_tries=config.requests_max_tries,
                requests_timeout=config.requests_timeout,
            ),
            scenario=scenario,
            source_code_format=config.source_code_format,
            esbmc_output_type=config.esbmc_output_type,
        )

        print()

        max_retries: int = config.fix_code_max_attempts
        for idx in range(max_retries):
            # Get a response. Use while loop to account for if the message stack
            # gets full, then need to compress and retry.
            llm_solution: str = ""
            while True:
                # Generate AI solution
                self.anim.start("Generating Solution... Please Wait")
                llm_solution, finish_reason = solution_generator.generate_solution()
                self.anim.stop()
                if finish_reason == FinishReason.length:
                    self.anim.start("Compressing message stack... Please Wait")
                    solution_generator.compress_message_stack()
                    self.anim.stop()
                else:
                    break

            # Print verbose lvl 2
            printvv("\nGeneration:")
            print_horizontal_line(2)
            printvv(llm_solution)
            print_horizontal_line(2)
            printvv("")

            # Pass to ESBMC, a workaround is used where the file is saved
            # to a temporary location since ESBMC needs it in file format.
            self.anim.start("Verifying with ESBMC... Please Wait")
            exit_code, esbmc_output = esbmc_load_source_code(
                file_path=file_name,
                source_code=llm_solution,
                esbmc_params=config.esbmc_params,
                auto_clean=config.temp_auto_clean,
                timeout=config.verifier_timeout,
            )
            self.anim.stop()

            # TODO Move this process into Solution Generator since have (beginning) is done
            # inside, and the other half is done here.
            try:
                esbmc_output = get_esbmc_output_formatted(
                    esbmc_output_type=config.esbmc_output_type,
                    esbmc_output=esbmc_output,
                )
            except ValueError:
                # Probably did not compile and so ESBMC source code is clang output.
                pass

            # Print verbose lvl 2
            print_horizontal_line(2)
            printvv(esbmc_output)
            print_horizontal_line(2)

            if exit_code == 0:
                self.on_solution_signal.emit(llm_solution)

                if config.raw_conversation:
                    print_raw_conversation()

                return False, llm_solution

            # Failure case
            print(f"Failure {idx+1}/{max_retries}: Retrying...")
            # If final iteration no need to sleep.
            if idx < max_retries - 1:

                # Inform solution generator chat about the ESBMC response.
                # TODO Add option to customize in config.
                if exit_code != 1:
                    # The program did not compile.
                    solution_generator.push_to_message_stack(
                        message=HumanMessage(
                            content=f"Here is the ESBMC output:\n\n```\n{esbmc_output}\n```"
                        )
                    )
                else:
                    solution_generator.push_to_message_stack(
                        message=HumanMessage(
                            content=f"Here is the ESBMC output:\n\n```\n{esbmc_output}\n```"
                        )
                    )

                solution_generator.push_to_message_stack(
                    AIMessage(content="Understood.")
                )

        if config.raw_conversation:
            print_raw_conversation()
        return True, "Failed all attempts..."
