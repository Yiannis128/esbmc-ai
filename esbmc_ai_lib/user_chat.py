# Author: Yiannis Charalambous 2023

from typing_extensions import override

from langchain.base_language import BaseLanguageModel
from langchain.memory import ConversationSummaryMemory, ChatMessageHistory
from langchain.schema import AIMessage, BaseMessage, HumanMessage, SystemMessage

from .ai_models import AIModel
from .base_chat_interface import BaseChatInterface


class UserChat(BaseChatInterface):
    solution: str = ""

    def __init__(
        self,
        system_messages: list,
        ai_model: AIModel,
        llm: BaseLanguageModel,
        source_code: str,
        esbmc_output: str,
    ) -> None:
        super().__init__(
            system_messages=system_messages,
            ai_model=ai_model,
            llm=llm,
        )

        self.push_to_message_stack(
            message=SystemMessage(
                content=f"Reply OK if you understand that the following text is the program source code:\n\n{source_code}"
            ),
            protected=True,
        )

        self.push_to_message_stack(message=AIMessage(content="OK"), protected=True)

        self.push_to_message_stack(
            message=SystemMessage(
                content=f"Reply OK if you understand that the following text is the output from ESBMC:\n\n{esbmc_output}",
            ),
            protected=True,
        )

        self.push_to_message_stack(message=AIMessage(content="OK"), protected=True)

    def set_solution(self, source_code: str) -> None:
        """Sets the solution to the problem ESBMC reported, this will inform the AI."""
        self.solution = source_code
        self.push_to_message_stack(
            message=HumanMessage(
                content=f"Here is the corrected code:\n\n{source_code}"
            ),
            protected=True,
        )

        self.push_to_message_stack(
            message=AIMessage(content="Understood"), protected=True
        )

    @override
    def compress_message_stack(self) -> None:
        """Uses ConversationSummaryMemory from Langchain to summarize the conversation of all the non-protected
        messages into one summary message which is added into the conversation as a SystemMessage.
        """
        # NOTE Need to find a solution to the problem that the protected messasges may be inbetween normal messages
        # hence the conversation summary may be incomplete.
        normal_messages: list[BaseMessage] = []
        for msg in self.messages:
            if msg not in self.protected_messages:
                normal_messages.append(msg)

        history: ChatMessageHistory = ChatMessageHistory(messages=normal_messages)
        memory: ConversationSummaryMemory = ConversationSummaryMemory.from_messages(
            llm=self.llm,
            chat_memory=history,
        )

        self.messages = self.protected_messages.copy()

        self.push_to_message_stack(SystemMessage(content=memory.buffer))
