"""ReAct agent graph, built by hand with LangGraph.

Usage (llama-server must be running, see serve.sh):
    python agent/graph.py "Which data releases are missing a DOI?"

Interface spec (Claude); everything else (Gary). Checked against langgraph 1.2.20 and
langchain-core 1.7.6:
- `from langgraph.graph import StateGraph, START, END`
- `from langgraph.graph.message import add_messages`  (reducer: appends instead of replacing)
- `from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage`
- `from langchain_openai import ChatOpenAI`; `.bind_tools(tools)` attaches the tool schemas.
The prebuilt alternative (for comparison at the end of A2) has moved to
`langchain.agents.create_agent` (separate `langchain` package, not installed yet);
`langgraph.prebuilt.create_react_agent` still exists but is deprecated.

The graph:

    START -> agent --(last message has tool calls and steps < MAX_STEPS)--> tools -> agent
                   \\--(otherwise)--> END

Design rules from A0/A1: keep SYSTEM_PROMPT short and identical on every call (prompt cache);
tool results are already compact; cap the model's reply length.
"""

import sys
import argparse
from typing import Annotated, TypedDict, Literal

from langchain_core.messages import AnyMessage,ToolMessage,SystemMessage,HumanMessage
from langgraph.graph import END,START
from langgraph.graph import add_messages
from langgraph.graph.state import StateGraph
from functools import partial

MAX_TOKENS = 256
MAX_STEPS = 4          # max agent turns that may call tools
BASE_URL = "http://127.0.0.1:8080/v1"

SYSTEM_PROMPT = """You will help a user search for ScienceBase items, provide item details, \
compute metrics based on metadata rules, or find metadata anomalies. Use the tools that are \
available to you rather than guess. The user cannot see tool results. Summarize what they show \
in plain language, e.g. the top few titles."""



class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]  # ✍ use the add_messages reducer
    steps: int                                  # agent turns so far


def make_llm( base_url=BASE_URL, max_tokens=512):
    """A chat model pointed at llama-server, with the tool schemas bound. Returns the runnable."""


    from langchain_openai import ChatOpenAI

    model = ChatOpenAI(
        model="llama-server",
        temperature=0,
        max_tokens=max_tokens,
        timeout=300,
        max_retries=2,
        api_key="api_key",
        base_url=base_url,
        # organization="...",
        # other params...
    )
    return model



    # raise NotImplementedError


def agent_node(state:AgentState, llm)->AgentState:
    """Call the model with SYSTEM_PROMPT + the conversation. Return the state update:
    the model's reply appended to messages, steps + 1."""
    response = llm.invoke([SystemMessage(content =SYSTEM_PROMPT )] + state['messages'])
    return {"messages": [response], "steps": state.get('steps',0) + 1}


def tool_node(state, tools):
    """Run every tool call in the last AI message, by hand (no prebuilt ToolNode).
    Return one ToolMessage per call, with the matching tool_call_id.
    Never raise: an unknown tool name, bad arguments or an exception inside a tool become a
    ToolMessage whose content explains the problem, so the model can try again."""
    tools_by_name={}
    for tool in tools:
        tools_by_name[tool.name] = tool
    last_message = state['messages'][-1]
    tool_messages = []
    for tool_call in last_message.tool_calls:
        status='success'
        try:
            if tool_call['name'] in tools_by_name:
                tool  = tools_by_name[tool_call['name']]
                tool_response = tool.invoke(tool_call['args'])
            else:
                tool_response = f"Could not find {tool_call['name']}. Available tools are {",".join(tools_by_name)}"
                status = 'error'
        except Exception as e:
            tool_response = str(e)[:100]
            status = 'error'
        tool_messages.append(ToolMessage(content=tool_response, tool_call_id=tool_call['id'],status=status))
    return {"messages":tool_messages}






def route(state:AgentState)->Literal['tools',END]:
    """Return "tools" if the last message has tool calls and steps < MAX_STEPS, else END."""
    messages = state['messages']
    last_message = messages[-1]
    if getattr(last_message,'tool_calls',None)  and state['steps'] < MAX_STEPS:
        return 'tools'
    else:
        return END
    # raise NotImplementedError


def build_graph(llm, tools):
    """Wire the nodes and edges above and return the compiled graph.
    `llm` is anything with .invoke(messages) -> AIMessage, so tests can pass a fake."""

    agent_builder = StateGraph(AgentState)
    agent_builder.add_node('agent',partial(agent_node,llm=llm))
    agent_builder.add_node('tools',partial(tool_node,tools=tools))
    agent_builder.add_edge(START,'agent')
    agent_builder.add_conditional_edges('agent',route,['tools',END])
    agent_builder.add_edge('tools','agent')
    agent = agent_builder.compile()
    return agent


    # raise NotImplementedError


def ask(graph, question):
    """Run one question through the graph; return the final state (dict with "messages")."""
    messages = [HumanMessage(content=question)]
    return  graph.invoke({'messages':messages})

    # raise NotImplementedError

def runner(stream:bool,query:str,render:bool):
    from tools import TOOLS
    llm = make_llm( base_url=BASE_URL, max_tokens=MAX_TOKENS).bind_tools(tools=TOOLS)


    graph = build_graph(llm=llm, tools=TOOLS)
    if render:
        print(graph.get_graph().draw_mermaid())
        sys.exit(0)
    import time

    if query:
        if stream:
            input_messages = [HumanMessage(content=query)]
            total_time = 0
            start = time.perf_counter()
            message_generator = graph.stream({'messages': input_messages, 'steps': 0}, stream_mode=['updates'],
                                             version='v2')
            for chunk in message_generator:
                if chunk["type"] == "updates":
                    for node_name, state in chunk["data"].items():
                        # print(f"Raw message: {state['messages']}")
                        message = state['messages'][0]
                        if hasattr(message, 'tool_calls') and len(message.tool_calls) > 0:
                            out_list = []
                            for tool_call in message.tool_calls:
                                out_list.append(f"{tool_call['name']}({tool_call['args']})")
                            summary = ",".join(out_list)
                        else:
                            summary = message.content
                        end = time.perf_counter()
                        elapsed = end - start
                        total_time += elapsed
                        print(f"[{elapsed:.2f}s] {node_name} summary: {summary}")
                        start = end
            print(f"total {total_time:.2f}s")
        else:
            messages = ask(graph, query)
            for message in messages['messages']:
                # end = time.perf_counter()
                # elapsed = end - start
                print(f"Message: {message.content_blocks}")
                if hasattr(message, 'usage_metadata'):
                    usage_metadata = message.usage_metadata
                    print(
                        f"input_tokens {usage_metadata.get('input_tokens', '')} output_tokens {usage_metadata.get('input_tokens', '')} cached tokens {usage_metadata.get('input_token_details', {}).get('cache_read', '')}")
                if hasattr(message, 'tool_calls'):
                    tool_calls = message.tool_calls
                    print(f"Tool calls {tool_calls}")
                # start = end

def main():
    """CLI: build the real llm and graph, ask the question from argv, print each step with
    its elapsed seconds, then the final answer."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("query", nargs="?")
    parser.add_argument('--render',action='store_true')
    args = parser.parse_args()
    runner(stream=True,query = args.query,render = args.render)


if __name__ == "__main__":
    main()
