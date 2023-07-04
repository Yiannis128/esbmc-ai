# Author: Yiannis Charalambous

from langchain.base_language import BaseLanguageModel
from langchain.llms.fake import FakeListLLM
from langchain.schema import HumanMessage, SystemMessage

from esbmc_ai_lib.ai_models import AIModel
from esbmc_ai_lib.user_chat import UserChat


def test_compress_message_stack() -> None:
    SUMMARY = "THIS IS A SUMMARY OF THE CONVERSATION"

    ai: AIModel = AIModel(name="test", tokens=12)

    llm: BaseLanguageModel = FakeListLLM(responses=[SUMMARY])

    chat: UserChat = UserChat(
        system_messages=[SystemMessage(content="This is a system message")],
        ai_model=ai,
        llm=llm,
        source_code="This is source code",
        esbmc_output="This is esbmc output",
    )

    # Compress with no unprotected message

    chat.compress_message_stack()
    assert chat.messages[-1].content == ""

    # Compress with unprotected message in the stack

    chat.push_to_message_stack(HumanMessage(content="Test message"))
    chat.compress_message_stack()

    assert chat.messages[-1] != chat.protected_messages[-1]
    assert chat.messages[-1].content == SUMMARY
