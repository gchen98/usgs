"""Checks for agent/graph.py. A scripted fake model stands in for the LLM, so these run
without llama-server. Run: python -m pytest -q tests/test_agent_graph.py"""

import sys
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agent"))
import graph  # noqa: E402


class FakeLLM:
    """Returns scripted replies in order (repeating the last), and records what it was sent."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def invoke(self, messages, *args, **kwargs):
        self.calls.append(list(messages))
        i = min(len(self.calls) - 1, len(self.replies) - 1)
        # A fresh copy without an id, like a real model's new reply. Returning the same object
        # twice would let add_messages treat it as an update to the earlier message.
        return self.replies[i].model_copy(update={"id": None})


def call(name, args, call_id="call_1"):
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id}])


@tool
def echo(text: str) -> str:
    """Return the text."""
    return f"echo: {text}"


@tool
def broken(text: str) -> str:
    """Always fails."""
    raise RuntimeError("disk on fire")


TOOLS = [echo, broken]


def run(replies, question="hi"):
    llm = FakeLLM(replies)
    state = graph.ask(graph.build_graph(llm, TOOLS), question)
    return llm, state["messages"]


def tool_messages(messages):
    return [m for m in messages if isinstance(m, ToolMessage)]


def test_system_prompt_is_real_and_sent_first():
    assert graph.SYSTEM_PROMPT.strip() not in ("", "✍")
    llm, _ = run([AIMessage(content="hello")])
    first = llm.calls[0]
    assert isinstance(first[0], SystemMessage) and first[0].content == graph.SYSTEM_PROMPT
    assert isinstance(first[1], HumanMessage) and first[1].content == "hi"


def test_direct_answer_makes_one_call():
    llm, messages = run([AIMessage(content="hello")])
    assert len(llm.calls) == 1
    assert messages[-1].content == "hello"


def test_one_tool_call_round_trip():
    llm, messages = run([call("echo", {"text": "x"}), AIMessage(content="done")])
    [tm] = tool_messages(messages)
    assert tm.tool_call_id == "call_1" and "echo: x" in tm.content
    assert any(isinstance(m, ToolMessage) for m in llm.calls[1])  # model saw the result
    assert messages[-1].content == "done"


def test_two_tool_calls_in_one_reply():
    reply = AIMessage(content="", tool_calls=[
        {"name": "echo", "args": {"text": "a"}, "id": "c1"},
        {"name": "echo", "args": {"text": "b"}, "id": "c2"},
    ])
    _, messages = run([reply, AIMessage(content="done")])
    assert {m.tool_call_id for m in tool_messages(messages)} == {"c1", "c2"}


def test_unknown_tool_becomes_a_message():
    _, messages = run([call("nope", {}), AIMessage(content="done")])
    [tm] = tool_messages(messages)
    assert "nope" in tm.content


def test_tool_exception_becomes_a_message():
    _, messages = run([call("broken", {"text": "x"}), AIMessage(content="done")])
    [tm] = tool_messages(messages)
    assert "disk on fire" in tm.content


def test_bad_arguments_become_a_message():
    _, messages = run([call("echo", {"wrong": 1}), AIMessage(content="done")])
    assert len(tool_messages(messages)) == 1


def test_step_limit_stops_a_looping_model():
    llm, messages = run([call("echo", {"text": "again"})])  # would loop forever
    assert len(llm.calls) == graph.MAX_STEPS
    assert len(tool_messages(messages)) <= graph.MAX_STEPS
