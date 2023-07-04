# Author: Yiannis Charalambous


from langchain.llms.fake import FakeListLLM
from langchain.schema import BaseMessage, HumanMessage, AIMessage, SystemMessage

from esbmc_ai_lib.ai_models import AIModel
from esbmc_ai_lib.chat_response import ChatResponse
from esbmc_ai_lib.base_chat_interface import BaseChatInterface


def test_push_message_stack(regtest) -> None:
    llm: FakeListLLM = FakeListLLM(responses=[])

    ai_model: AIModel = AIModel("test", 1024)

    chat: BaseChatInterface = BaseChatInterface(
        ai_model=ai_model,
        system_messages=[],
        llm=llm,
    )

    messages: list[BaseMessage] = [
        AIMessage(content="Test 1"),
        HumanMessage(content="Test 2"),
        SystemMessage(content="Test 3"),
    ]

    chat.push_to_message_stack(message=messages[0], protected=False)
    chat.push_to_message_stack(message=messages[1], protected=True)
    chat.push_to_message_stack(message=messages[2], protected=True)

    with regtest:
        print(chat.protected_messages)
        print(chat.messages)


def test_send_message(regtest) -> None:
    responses: list[str] = ["OK 1", "OK 2", "OK 3"]
    llm: FakeListLLM = FakeListLLM(responses=responses)

    ai_model: AIModel = AIModel("test", 6)

    sys: list[BaseMessage] = []
    chat: BaseChatInterface = BaseChatInterface(
        ai_model=ai_model,
        system_messages=sys,
        llm=llm,
    )

    chat_responses: list[ChatResponse] = [
        chat.send_message("Test 1"),
        chat.send_message("Test 2"),
        chat.send_message("Test 3"),
    ]

    with regtest:
        print(chat_responses)
        print(chat.protected_messages)
        print(chat.messages)
