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
from ..esbmc_util import esbmc_load_source_code
from ..solution_generator import SolutionGenerator
from ..logging import printv, printvv

# TODO Remove built in messages and move them to config.


class FixCodeCommand(ChatCommand):
    on_solution_signal: Signal = Signal()

    def __init__(self) -> None:
        super().__init__(
            command_name="fix-code",
            help_message="Generates a solution for this code, and reevaluates it with ESBMC.",
        )
        self.anim = create_loading_widget()

    def _resolve_scenario(self, esbmc_output: str) -> str:
        # Start search from the marker.
        marker: str = "Violated property:\n"
        violated_property_index: int = esbmc_output.rfind(marker) + len(marker)
        from_loc_error_msg: str = esbmc_output[violated_property_index:]
        # Find second new line which contains the location of the violated
        # property and that should point to the line with the type of error.
        # In this case, the type of error is the "scenario".
        scenario_index: int = from_loc_error_msg.find("\n")
        scenario: str = from_loc_error_msg[scenario_index + 1 :]
        scenario_end_l_index: int = scenario.find("\n")
        scenario = scenario[:scenario_end_l_index].strip()
        return scenario

    @override
    def execute(self, **kwargs: Any) -> Tuple[bool, str]:
        file_name: str = kwargs["file_name"]
        source_code: str = kwargs["source_code"]
        esbmc_output: str = kwargs["esbmc_output"]

        # Parse the esbmc output here and determine what "Scenario" to use.
        scenario: str = self._resolve_scenario(esbmc_output)

        printv(f"Scenario: {scenario}")
        printv(
            f"Using dynamic prompt..."
            if scenario in config.chat_prompt_generator_mode.scenarios
            else "Using generic prompt..."
        )

        llm = config.ai_model.create_llm(
            api_keys=config.api_keys,
            temperature=config.chat_prompt_generator_mode.temperature,
            requests_max_tries=config.requests_max_tries,
            requests_timeout=config.requests_timeout,
        )

        solution_generator = SolutionGenerator(
            ai_model_agent=config.chat_prompt_generator_mode,
            source_code=source_code,
            esbmc_output=esbmc_output,
            ai_model=config.ai_model,
            llm=llm,
            scenario=scenario,
        )

        print()

        max_retries: int = 10
        for idx in range(max_retries):
            # Get a response. Use while loop to account for if the message stack
            # gets full, then need to compress and retry.
            response: str = ""
            while True:
                # Generate AI solution
                self.anim.start("Generating Solution... Please Wait")
                response, finish_reason = solution_generator.generate_solution()
                self.anim.stop()
                if finish_reason == FinishReason.length:
                    self.anim.start("Compressing message stack... Please Wait")
                    solution_generator.compress_message_stack()
                    self.anim.stop()
                else:
                    break

            # Print verbose lvl 2
            printvv("\nGeneration:")
            printvv("-" * get_terminal_size().columns)
            printvv(response)
            printvv("-" * get_terminal_size().columns)
            printvv("")

            # Pass to ESBMC, a workaround is used where the file is saved
            # to a temporary location since ESBMC needs it in file format.
            self.anim.start("Verifying with ESBMC... Please Wait")
            exit_code, esbmc_output, esbmc_err_output = esbmc_load_source_code(
                file_path=file_name,
                source_code=str(response),
                esbmc_params=config.esbmc_params,
                auto_clean=config.temp_auto_clean,
                timeout=config.verifier_timeout,
            )
            self.anim.stop()

            # Print verbose lvl 2
            printvv("-" * get_terminal_size().columns)
            printvv(esbmc_output)
            printvv(esbmc_err_output)
            printvv("-" * get_terminal_size().columns)

            if exit_code == 0:
                self.on_solution_signal.emit(response)
                return False, response

            # Failure case
            print(f"Failure {idx+1}/{max_retries}: Retrying...")
            # If final iteration no need to sleep.
            if idx < max_retries - 1:

                # Inform solution generator chat about the ESBMC response.
                if exit_code != 1:
                    # The program did not compile.
                    solution_generator.push_to_message_stack(
                        message=HumanMessage(
                            content=f"The source code you provided does not compile. Fix the compilation errors. Use ESBMC output to fix the compilation errors:\n\n```\n{esbmc_output}\n```"
                        )
                    )
                else:
                    solution_generator.push_to_message_stack(
                        message=HumanMessage(
                            content=f"ESBMC has reported that verification failed, use the ESBMC output to find out what is wrong, and fix it. Here is ESBMC output:\n\n```\n{esbmc_output}\n```"
                        )
                    )

                solution_generator.push_to_message_stack(
                    AIMessage(content="Understood.")
                )

        return True, "Failed all attempts..."
