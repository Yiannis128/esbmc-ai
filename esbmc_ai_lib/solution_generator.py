# Author: Yiannis Charalambous 2023

from typing_extensions import override
from langchain.base_language import BaseLanguageModel

from langchain.schema import AIMessage, BaseMessage, HumanMessage

from esbmc_ai_lib.chat_response import ChatResponse, FinishReason

from .ai_models import AIModel
from .base_chat_interface import BaseChatInterface


class SolutionGenerator(BaseChatInterface):
    initial_prompt: str
    source_code: str
    esbmc_output: str

    def __init__(
        self,
        system_messages: list[BaseMessage],
        llm: BaseLanguageModel,
        initial_prompt: str,
        source_code: str,
        esbmc_output: str,
        ai_model: AIModel,
    ) -> None:
        super().__init__(
            system_messages=system_messages,
            ai_model=ai_model,
            llm=llm,
        )
        self.initial_prompt = initial_prompt
        self.source_code = source_code
        self.esbmc_output = esbmc_output

        # Introduce source code and ESBMC output to AI.
        self.push_to_message_stack(
            message=HumanMessage(
                content=f"The following text is the source code of the program, reply OK if you understand:\n\n{source_code}"
            ),
            protected=True,
        )
        self.push_to_message_stack(message=AIMessage(content="OK"), protected=True)
        self.push_to_message_stack(
            message=HumanMessage(
                content=f"The following text is the output of ESBMC, reply OK if you understand:\n\n{esbmc_output}"
            ),
            protected=True,
        )
        self.push_to_message_stack(message=AIMessage(content="OK"), protected=True)

    @override
    def compress_message_stack(self) -> None:
        # Resets the conversation - cannot summarize code
        self.messages = self.protected_messages.copy()

    def generate_solution(self) -> tuple[str, FinishReason]:
        response: ChatResponse = self.send_message(self.initial_prompt, False)
        solution: str = response.message.content

        # Strip the source code of any leftover text as sometimes the AI model
        # will generate text and formatting despite being told not to.
        try:
            code_start: int = solution.index("```") + 3
            # Remove up until the new line, because usually there's a language
            # specification after the 3 ticks ```c...
            code_start = solution.index("\n", code_start)
            code_end: int = len(solution) - 3 - solution[::-1].index("```")
            solution = solution[code_start:code_end]
        except ValueError:
            pass

        return solution, response.finish_reason
