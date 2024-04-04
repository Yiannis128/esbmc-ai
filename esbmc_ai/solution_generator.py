# Author: Yiannis Charalambous 2023

from re import S
from typing import Optional
from typing_extensions import override
from langchain.base_language import BaseLanguageModel
from langchain.schema import BaseMessage, HumanMessage

from esbmc_ai.chat_response import ChatResponse, FinishReason
from esbmc_ai.config import ChatPromptSettings, DynamicAIModelAgent
from esbmc_ai.frontend.solution import apply_line_patch

from .ai_models import AIModel
from .base_chat_interface import BaseChatInterface
from esbmc_ai.esbmc_util import (
    esbmc_get_counter_example,
    esbmc_get_violated_property,
    get_source_code_err_line_idx,
)


def get_source_code_formatted(
    source_code_format: str, source_code: str, esbmc_output: str
) -> str:
    match source_code_format:
        case "single":
            line: Optional[int] = get_source_code_err_line_idx(esbmc_output)
            assert line, "error line not found in esbmc output"
            # ESBMC reports errors starting from 1. To get the correct line, we need to use 0 based
            # indexing.
            return source_code.splitlines(True)[line]
        case "full":
            return source_code
        case _:
            raise ValueError(
                f"Not a valid format for source code: {source_code_format}"
            )


def get_esbmc_output_formatted(esbmc_output_type: str, esbmc_output: str) -> str:
    match esbmc_output_type:
        case "vp":
            value: Optional[str] = esbmc_get_violated_property(esbmc_output)
            if not value:
                raise ValueError("Not found violated property.")
            return value
        case "ce":
            value: Optional[str] = esbmc_get_counter_example(esbmc_output)
            if not value:
                raise ValueError("Not found counterexample.")
            return value
        case "full":
            return esbmc_output
        case _:
            raise ValueError(f"Not a valid ESBMC output type: {esbmc_output_type}")


class SolutionGenerator(BaseChatInterface):
    def __init__(
        self,
        ai_model_agent: DynamicAIModelAgent,
        llm: BaseLanguageModel,
        source_code: str,
        esbmc_output: str,
        ai_model: AIModel,
        scenario: str = "",
        source_code_format: str = "full",
        esbmc_output_type: str = "full",
    ) -> None:
        # Convert to chat prompt
        chat_prompt: ChatPromptSettings = DynamicAIModelAgent.to_chat_prompt_settings(
            ai_model_agent=ai_model_agent, scenario=scenario
        )

        super().__init__(
            ai_model_agent=chat_prompt,
            ai_model=ai_model,
            llm=llm,
        )
        self.initial_prompt = ai_model_agent.initial_prompt

        self.esbmc_output_type: str = esbmc_output_type
        self.esbmc_output = get_esbmc_output_formatted(
            esbmc_output_type=self.esbmc_output_type,
            esbmc_output=esbmc_output,
        )

        self.source_code_format: str = source_code_format
        self.source_code_raw: str = source_code

        source_code_formatted: str = get_source_code_formatted(
            source_code_format=self.source_code_format,
            source_code=self.source_code_raw,
            esbmc_output=self.esbmc_output,
        )

        self.apply_template_value(
            source_code=source_code_formatted,
            esbmc_output=self.esbmc_output,
        )

    @override
    def compress_message_stack(self) -> None:
        # Resets the conversation - cannot summarize code
        self.messages: list[BaseMessage] = []

    @classmethod
    def get_code_from_solution(cls, solution: str) -> str:
        """Strip the source code of any leftover text as sometimes the AI model
        will generate text and formatting despite being told not to."""
        try:
            code_start: int = solution.index("```") + 3
            assert code_start != -1

            # Remove up until the new line, because usually there's a language
            # specification after the 3 ticks ```c...
            code_start = solution.index("\n", code_start) + 1
            assert code_start != -1

            code_end: int = solution[::-1].index("```")
            assert code_start != -1

            # -4 = 3 backticks and also the \n before the backticks.
            code_end: int = len(solution) - 4 - code_end
            assert code_start <= code_end

            solution = solution[code_start:code_end]
        except (ValueError, AssertionError):
            pass
        return solution

    def generate_solution(self) -> tuple[str, FinishReason]:
        response: ChatResponse = self.send_message(self.initial_prompt)
        solution: str = str(response.message.content)

        solution = SolutionGenerator.get_code_from_solution(solution)

        # If source code passed to LLM is formatted then we need to recombine to
        # full source code before giving to ESBMC
        match self.source_code_format:
            case "single":
                err_line: Optional[int] = get_source_code_err_line_idx(
                    self.esbmc_output
                )
                assert (
                    err_line
                ), "fix code command: error line could not be found to apply brutal patch replacement"
                solution = apply_line_patch(
                    self.source_code_raw, solution, err_line, err_line
                )

        return solution, response.finish_reason
