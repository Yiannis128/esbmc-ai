# Author: Yiannis Charalambous

from abc import abstractmethod

from langchain.base_language import BaseLanguageModel
from langchain.callbacks import get_openai_callback
from langchain.schema import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    LLMResult,
    PromptValue,
)

from openai import InvalidRequestError
from text_generation.errors import UnknownError, ValidationError

from .chat_response import ChatResponse, FinishReason
from .ai_models import AIModel, AIModelOpenAI


class BaseChatInterface(object):
    protected_messages: list[BaseMessage]
    messages: list[BaseMessage]
    ai_model: AIModel
    llm: BaseLanguageModel

    def __init__(
        self,
        system_messages: list[BaseMessage],
        llm: BaseLanguageModel,
        ai_model: AIModel,
    ) -> None:
        super().__init__()
        self.ai_model = ai_model

        self.protected_messages = system_messages.copy()
        self.messages = system_messages.copy()

        self.llm = llm

    @abstractmethod
    def compress_message_stack(self) -> None:
        raise NotImplementedError()

    def push_to_message_stack(
        self, message: BaseMessage, protected: bool = False
    ) -> None:
        if protected:
            self.protected_messages.append(message)
        self.messages.append(message)

    # Returns an OpenAI object back.
    def send_message(self, message: str, protected: bool = False) -> ChatResponse:
        """Sends a message to the AI model. Returns solution."""
        self.push_to_message_stack(
            message=HumanMessage(content=message),
            protected=protected,
        )

        # Transform message stack to ChatPromptValue: If this is a ChatLLM then the
        # function will simply be an identity function that does nothing and simply
        # returns the messages as a ChatPromptValue. If this is a text generation
        # LLM, then the function should inject the config message around the
        # conversation to make the LLM behave like a ChatLLM.
        message_prompts: PromptValue = self.ai_model.apply_chat_template(
            messages=self.messages,
        )

        # TODO When token counting comes to other models, implement it.
        # Need to implement ai_model.tokens...

        response: ChatResponse
        with get_openai_callback() as cb:
            try:
                result: LLMResult = self.llm.generate_prompt(
                    prompts=[message_prompts],
                )

                response_message: BaseMessage = AIMessage(
                    content=result.generations[0][0].text
                )

                self.push_to_message_stack(
                    message=response_message, protected=protected
                )

                response = ChatResponse(
                    finish_reason=FinishReason.stop,
                    message=response_message,
                    total_tokens=cb.total_tokens,
                )
            except ValidationError as e:
                # HFTextGen
                response = ChatResponse(
                    finish_reason=FinishReason.length,
                    # NOTE Show the total tokens of the model instead of 0
                    # (no token counting currently...)
                    total_tokens=self.ai_model.tokens,
                )
            except InvalidRequestError as e:
                # OpenAI model error handling.
                if e.code == AIModelOpenAI.context_length_exceeded_error:
                    response = ChatResponse(
                        finish_reason=FinishReason.length,
                        total_tokens=cb.total_tokens,
                    )
                else:
                    raise
            except UnknownError as e:
                # HFTextGen
                print(f"There was an unkown error when generating a response: {e}")
                exit(1)
            except Exception:
                raise

        return response
