# Author: Yiannis Charalambous

from abc import abstractmethod
from typing import Any, Iterable, Union
from enum import Enum
from pydantic.v1.types import SecretStr
from typing_extensions import override

from langchain.prompts import PromptTemplate
from langchain.base_language import BaseLanguageModel

from langchain_openai import ChatOpenAI
from langchain_community.llms.huggingface_text_gen_inference import (
    HuggingFaceTextGenInference,
)

from langchain.prompts.chat import (
    AIMessagePromptTemplate,
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain.schema import (
    BaseMessage,
    PromptValue,
)


from esbmc_ai.api_key_collection import APIKeyCollection


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
        requests_max_tries: int = 5,
        requests_timeout: float = 60,
    ) -> BaseLanguageModel:
        """Initializes a large language model model with the provided parameters."""
        raise NotImplementedError()

    @classmethod
    def convert_messages_to_tuples(
        cls, messages: Iterable[BaseMessage]
    ) -> list[tuple[str, str]]:
        """Converts messages into a format understood by the ChatPromptTemplate - since it won't format
        BaseMessage derived classes for some reason, but will for tuples, because they get converted into
        Templates in function `_convert_to_message`."""
        return [(message.type, str(message.content)) for message in messages]

    @classmethod
    def escape_messages(
        cls,
        messages: Iterable[BaseMessage],
        allowed_keys: list[str],
    ) -> Iterable[BaseMessage]:
        """Adds escape curly braces to the messages, will make sure that the sequential
        curly braces in the messages is even (and hence escaped). Will ignore curly braces
        with `allowed_keys`."""

        def add_safeguards(content: str, char: str, allowed_keys: list[str]) -> str:
            start_idx: int = 0
            while True:
                char_idx: int = content.find(char, start_idx)
                if char_idx == -1:
                    break
                # Count how many sequences of the char are occuring
                count: int = 1
                # FIXME Add bounds check here
                while (
                    len(content) > char_idx + count
                    and content[char_idx + count] == char
                ):
                    count += 1

                # Check if the next sequence is in the allowed keys, if it is, then
                # skip to the next one.
                is_allowed: bool = False
                for key in allowed_keys:
                    if key == content[char_idx + count : char_idx + count + len(key)]:
                        is_allowed = True
                        break

                # Now change start_idx to reflect new location. The start index is at the end of
                # all the chars (including the inserted one).
                start_idx = char_idx + count + 1

                # If inside allowed keys, then continue to next iteration.
                if is_allowed:
                    continue

                # Check if odd number (will need to add extra char)
                if count % 2 != 0:
                    content = (
                        content[: char_idx + count] + char + content[char_idx + count :]
                    )
            return content

        reversed_keys: list[str] = [key[::-1] for key in allowed_keys]

        result: list[BaseMessage] = []
        for msg in messages:
            content: str = str(msg.content)
            look_pointer: int = 0
            # Open curly check
            if content.find("{", look_pointer) != -1:
                content = add_safeguards(content, "{", allowed_keys)
            # Close curly check
            if content.find("}", look_pointer) != -1:
                # Do it in reverse with reverse keys.
                content = add_safeguards(content[::-1], "}", reversed_keys)[::-1]
            new_msg = msg.copy()
            new_msg.content = content
            result.append(new_msg)
        return result

    def apply_chat_template(
        self,
        messages: Iterable[BaseMessage],
        **format_values: Any,
    ) -> PromptValue:
        # Default one, identity function essentially.
        escaped_messages = AIModel.escape_messages(messages, list(format_values.keys()))
        message_tuples = AIModel.convert_messages_to_tuples(escaped_messages)
        return ChatPromptTemplate.from_messages(messages=message_tuples).format_prompt(
            **format_values,
        )


class AIModelOpenAI(AIModel):
    context_length_exceeded_error: str = "context_length_exceeded"
    """Error code for when the length has been reached."""

    @override
    def create_llm(
        self,
        api_keys: APIKeyCollection,
        temperature: float = 1.0,
        requests_max_tries: int = 5,
        requests_timeout: float = 60,
    ) -> BaseLanguageModel:
        return ChatOpenAI(
            model=self.name,
            api_key=SecretStr(api_keys.openai),
            max_tokens=None,
            temperature=temperature,
            max_retries=requests_max_tries,
            timeout=requests_timeout,
            model_kwargs={},
        )


class AIModelTextGen(AIModel):
    """Below are only used for models that need them, such as models that
    are using the provider "text_inference_server"."""

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

        self.url: str = url
        self.chat_template: PromptTemplate = PromptTemplate.from_template(
            template=config_message,
        )
        """The chat template to place all messages in."""

        self.system_template: SystemMessagePromptTemplate = (
            SystemMessagePromptTemplate.from_template(
                template=system_template,
            )
        )
        """Template for each system message."""

        self.human_template: HumanMessagePromptTemplate = (
            HumanMessagePromptTemplate.from_template(
                template=human_template,
            )
        )
        """Template for each human message."""

        self.ai_template: AIMessagePromptTemplate = (
            AIMessagePromptTemplate.from_template(
                template=ai_template,
            )
        )
        """Template for each AI message."""

        self.stop_sequences: list[str] = stop_sequences

    @override
    def create_llm(
        self,
        api_keys: APIKeyCollection,
        temperature: float = 1.0,
        requests_max_tries: int = 5,
        requests_timeout: float = 60,
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
            max_retries=requests_max_tries,
            timeout=requests_timeout,
        )

    @override
    def apply_chat_template(
        self,
        messages: Iterable[BaseMessage],
        **format_values: Any,
    ) -> PromptValue:
        """Text generation LLMs take single string of text as input. So the conversation
        is converted into a string and returned back in a single prompt value. The config
        message is also applied to the conversation."""

        escaped_messages = AIModel.escape_messages(messages, list(format_values.keys()))

        formatted_messages: list[BaseMessage] = []
        for msg in escaped_messages:
            formatted_msg: BaseMessage
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

        return self.chat_template.format_prompt(
            history="\n\n".join([str(msg.content) for msg in formatted_messages[:-1]]),
            user_prompt=formatted_messages[-1].content,
            **format_values,
        )


class AIModels(Enum):
    GPT_3 = AIModelOpenAI(name="gpt-3.5-turbo", tokens=4096)
    GPT_3_16K = AIModelOpenAI(name="gpt-3.5-turbo-16k", tokens=16384)
    GPT_4 = AIModelOpenAI(name="gpt-4", tokens=8192)
    GPT_4_32K = AIModelOpenAI(name="gpt-4-32k", tokens=32768)
    GPT_4_TURBO_PREVIEW= AIModelOpenAI(name="gpt-4-turbo-preview", tokens=128000)    
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
