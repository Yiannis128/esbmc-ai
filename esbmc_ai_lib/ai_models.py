# Author: Yiannis Charalambous

from abc import abstractmethod
from typing import Union
from enum import Enum
from typing_extensions import override

from langchain.base_language import BaseLanguageModel
from langchain.chat_models import ChatOpenAI
from langchain.llms import HuggingFaceTextGenInference

from langchain.prompts import PromptTemplate
from langchain.prompts.chat import ChatPromptValue
from langchain.schema import (
    BaseMessage,
    PromptValue,
)

from openai import ChatCompletion as OpenAIChatCompletion

from esbmc_ai_lib.api_key_collection import APIKeyCollection


class AIModel(object):
    name: str
    tokens: int

    def __init__(
        self,
        name: str,
        tokens: int,
    ) -> None:
        self.name = name
        self.tokens = tokens

    @abstractmethod
    def create_llm(
        self,
        api_keys: APIKeyCollection,
        temperature: float = 1.0,
    ) -> BaseLanguageModel:
        raise NotImplementedError()

    def apply_chat_template(
        self,
        messages: list[BaseMessage],
    ) -> PromptValue:
        # Default one, identity function essentially.
        return ChatPromptValue(messages=messages)


class AIModelOpenAI(AIModel):
    context_length_exceeded_error: str = "context_length_exceeded"
    """Error code for when the length has been reached."""

    @override
    def create_llm(
        self,
        api_keys: APIKeyCollection,
        temperature: float,
    ) -> BaseLanguageModel:
        return ChatOpenAI(
            client=OpenAIChatCompletion,
            model=self.name,
            openai_api_key=api_keys.openai,
            max_tokens=None,
            temperature=temperature,
            model_kwargs={},
        )


class AIModelTextGen(AIModel):
    # Below are only used for models that need them, such as models that
    # are using the provider "text_inference_server".
    url: str
    config_message: str
    """The config message to place all messages in."""
    system_template: PromptTemplate
    """Template for each system message."""
    human_template: PromptTemplate
    """Template for each human message."""
    ai_template: PromptTemplate
    """Template for each AI message."""
    stop_sequences: list[str]

    def __init__(
        self,
        name: str,
        tokens: int,
        url: str,
        config_message: str = "{history}\n\n{user_prompt}",
        system_template: str = "{content}",
        human_template: str = "{content}",
        ai_template: str = "{content}",
        stop_sequences: list[str] = [],
    ) -> None:
        super().__init__(name, tokens)

        self.url = url
        self.config_message = config_message

        self.system_template = PromptTemplate(
            input_variables=["content"],
            template=system_template,
        )

        self.human_template = PromptTemplate(
            input_variables=["content"],
            template=human_template,
        )

        self.ai_template = PromptTemplate(
            input_variables=["content"],
            template=ai_template,
        )

        self.stop_sequences = stop_sequences

    @override
    def create_llm(
        self,
        api_keys: APIKeyCollection,
        temperature: float,
    ) -> BaseLanguageModel:
        return HuggingFaceTextGenInference(
            client=None,
            async_client=None,
            inference_server_url=self.url,
            server_kwargs={
                "headers": {"Authorization": f"Bearer {api_keys.huggingface}"}
            },
            # FIXME Need to find a way to make output bigger. When token
            # tracking for this LLM type is added.
            max_new_tokens=5000,
            temperature=temperature,
            stop_sequences=self.stop_sequences,
        )

    @override
    def apply_chat_template(self, messages: list[BaseMessage]) -> PromptValue:
        """Text generation LLMs take single string of text as input. So the conversation
        is converted into a string and returned back in a single prompt value. The config
        message is also applied to the conversation."""

        formatted_messages: list[str] = []
        for msg in messages:
            formatted_msg: str
            if msg.type == "ai":
                formatted_msg = self.ai_template.format(content=msg.content)
            elif msg.type == "system":
                formatted_msg = self.system_template.format(content=msg.content)
            elif msg.type == "human":
                formatted_msg = self.human_template.format(content=msg.content)
            else:
                raise ValueError(
                    f"Got unsupported message type: {msg.type}: {msg.content}"
                )
            formatted_messages.append(formatted_msg)

        config_message_template: PromptTemplate = PromptTemplate(
            template=self.config_message,
            input_variables=["history", "user_prompt"],
        )

        # Get formatted string of each history message and separate it using new
        # lines, each message is then joined into a single string.
        formatted_history: str = "\n\n".join(formatted_messages[:-1])

        chat_prompt: PromptValue = config_message_template.format_prompt(
            history=formatted_history,
            user_prompt=formatted_messages[-1],
        )

        return chat_prompt


class AIModels(Enum):
    GPT_3 = AIModelOpenAI(name="gpt-3.5-turbo", tokens=4096)
    GPT_3_16K = AIModelOpenAI(name="gpt-3.5-turbo-16k", tokens=16384)
    GPT_4 = AIModelOpenAI(name="gpt-4", tokens=8192)
    GPT_4_32K = AIModelOpenAI(name="gpt-4-32k", tokens=32768)
    FALCON_7B = AIModelTextGen(
        name="falcon-7b",
        tokens=8192,
        url="https://api-inference.huggingface.co/models/tiiuae/falcon-7b-instruct",
        config_message='>>DOMAIN<<You are a helpful assistant that answers any questions asked based on the previous messages in the conversation. The questions are asked by Human. The "AI" is the assistant. The AI shall not impersonate any other entity in the interaction including System and Human. The Human may refer to the AI directly, the AI should refer to the Human directly back, for example, when asked "How do you suggest a fix?", the AI shall respond "You can try...". The AI should use markdown formatting in its responses. The AI should follow the instructions given by System.\n\n>>SUMMARY<<{history}\n\n{user_prompt}\n\n',
        ai_template=">>ANSWER<<{content}",
        human_template=">>QUESTION<<Human:{content}>>ANSWER<<",
        system_template="System: {content}",
    )
    STARCHAT_BETA = AIModelTextGen(
        name="starchat-beta",
        tokens=8192,
        url="https://api-inference.huggingface.co/models/HuggingFaceH4/starchat-beta",
        config_message="{history}\n{user_prompt}\n<|assistant|>\n",
        system_template="<|system|>\n{content}\n<|end|>",
        ai_template="<|assistant|>\n{content}\n<|end|>",
        human_template="<|user|>\n{content}\n<|end|>",
        stop_sequences=["<|end|>"],
    )


_custom_ai_models: list[AIModel] = []

_ai_model_names: set[str] = set(item.value.name for item in AIModels)


def add_custom_ai_model(ai_model: AIModel) -> None:
    """Registers a custom AI model."""
    # Check if AI already already exists.
    if ai_model.name in _ai_model_names:
        raise Exception(f'AI Model "{ai_model.name}" already exists...')
    _ai_model_names.add(ai_model.name)
    _custom_ai_models.append(ai_model)


def is_valid_ai_model(ai_model: Union[str, AIModel]) -> bool:
    """Accepts both the AIModel object and the name as parameter."""
    name: str
    if isinstance(ai_model, AIModel):
        name = ai_model.name
    else:
        name = ai_model
    return name in _ai_model_names


def get_ai_model_by_name(name: str) -> AIModel:
    # Check AIModels enum.
    for enum_value in AIModels:
        ai_model: AIModel = enum_value.value
        if name == ai_model.name:
            return ai_model

    # Check custom AI models.
    for custom_ai in _custom_ai_models:
        if name == custom_ai.name:
            return custom_ai

    raise Exception(f'The AI "{name}" was not found...')
