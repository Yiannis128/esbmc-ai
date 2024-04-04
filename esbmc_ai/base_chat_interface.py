# Author: Yiannis Charalambous

from abc import abstractmethod
from typing import Optional

from langchain.base_language import BaseLanguageModel
from langchain.schema import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    LLMResult,
    PromptValue,
)

from esbmc_ai.config import ChatPromptSettings
from .chat_response import ChatResponse, FinishReason
from .ai_models import AIModel


class BaseChatInterface(object):
    def __init__(
        self,
        ai_model_agent: ChatPromptSettings,
        llm: BaseLanguageModel,
        ai_model: AIModel,
    ) -> None:
        super().__init__()
        self.ai_model: AIModel = ai_model
        self.ai_model_agent: ChatPromptSettings = ai_model_agent
        self._system_messages: list[BaseMessage] = list(
            ai_model_agent.system_messages.messages
        )
        self.messages: list[BaseMessage] = []
        self.llm: BaseLanguageModel = llm

    @abstractmethod
    def compress_message_stack(self) -> None:
        raise NotImplementedError()

    def push_to_message_stack(
        self,
        message: BaseMessage,
    ) -> None:
        self.messages.append(message)

    def apply_template_value(self, **kwargs: str) -> None:
        """Will substitute an f-string in the message stack and system messages to
        the provided value."""

        system_message_prompts: PromptValue = self.ai_model.apply_chat_template(
            messages=self._system_messages,
            **kwargs,
        )
        self._system_messages = system_message_prompts.to_messages()

        message_prompts: PromptValue = self.ai_model.apply_chat_template(
            messages=self.messages,
            **kwargs,
        )
        self.messages = message_prompts.to_messages()

    def get_applied_messages(self, **kwargs: str) -> tuple[BaseMessage, ...]:
        """Applies the f-string substituion and returns the result instead of assigning
        it to the message stack."""
        message_prompts: PromptValue = self.ai_model.apply_chat_template(
            messages=self.messages,
            **kwargs,
        )
        return tuple(message_prompts.to_messages())

    def get_applied_system_messages(self, **kwargs: str) -> tuple[BaseMessage, ...]:
        """Same as `get_applied_messages` but for system messages."""
        message_prompts: PromptValue = self.ai_model.apply_chat_template(
            messages=self._system_messages,
            **kwargs,
        )
        return tuple(message_prompts.to_messages())

    def send_message(self, message: Optional[str] = None) -> ChatResponse:
        """Sends a message to the AI model. Returns solution."""
        if message:
            self.push_to_message_stack(message=HumanMessage(content=message))

        all_messages = self._system_messages.copy()
        all_messages.extend(self.messages.copy())

        # Transform message stack to ChatPromptValue: If this is a ChatLLM then the
        # function will simply be an identity function that does nothing and simply
        # returns the messages as a ChatPromptValue. If this is a text generation
        # LLM, then the function should inject the config message around the
        # conversation to make the LLM behave like a ChatLLM.
        # Do not replace any values.
        message_prompts: PromptValue = self.ai_model.apply_chat_template(
            messages=all_messages,
        )

        response: ChatResponse
        try:
            result: LLMResult = self.llm.generate_prompt(
                prompts=[message_prompts],
            )

            response_message: BaseMessage = AIMessage(
                content=result.generations[0][0].text
            )

            self.push_to_message_stack(message=response_message)

            # Check if token limit has been exceeded.
            all_messages.append(response_message)
            new_tokens: int = self.llm.get_num_tokens_from_messages(
                messages=all_messages,
            )
            if new_tokens > self.ai_model.tokens:
                response = ChatResponse(
                    finish_reason=FinishReason.length,
                    message=response_message,
                    total_tokens=self.ai_model.tokens,
                )
            else:
                response = ChatResponse(
                    finish_reason=FinishReason.stop,
                    message=response_message,
                    total_tokens=new_tokens,
                )
        except Exception as e:
            print(f"There was an unkown error when generating a response: {e}")
            exit(1)

        return response
