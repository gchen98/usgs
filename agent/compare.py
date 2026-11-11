"""Comparison of langgraph vs langchain versions of a toy agent.

Usage (llama-server must be running, see serve.sh):
    Example: python agent/compare.py "Give me details on item with ID Gary” --graph custom --iterations 5 --warmupsteps 2


"""

import sys
import argparse

MAX_STEPS = 4          # max agent turns that may call tools
BASE_URL = "http://127.0.0.1:8080/v1"


def prebuilt_runner(query:str):
    from langchain.agents import create_agent
    from tools import TOOLS
    import graph
    agent = create_agent(
        model=graph.make_llm(base_url = graph.BASE_URL,max_tokens = graph.MAX_TOKENS),
        tools=TOOLS,
        system_prompt=graph.SYSTEM_PROMPT,
    )
    result = agent.invoke(
        {"messages": [{"role": "user", "content": query}]}
    )
    for message in result['messages']:
        print(f"Message: {message.content_blocks}")
        if hasattr(message,'usage_metadata'):
            usage_metadata = message.usage_metadata
            print(f"input_tokens {usage_metadata.get('input_tokens','')} output_tokens {usage_metadata.get('input_tokens','')} cached tokens {usage_metadata.get('input_token_details', {}).get('cache_read','')}")
        if hasattr(message,'tool_calls'):
            tool_calls = message.tool_calls
            print(f"Tool calls {tool_calls}")


def main():
    """CLI: build the real llm and graph, ask the question from argv, print each step with
    its elapsed seconds, then the final answer."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("query", nargs="?")
    parser.add_argument('--graph', help="valid values are 'pre-built' or 'custom'")
    parser.add_argument('--warmupsteps', help="steps where timings are discarded",type=int)
    parser.add_argument('--iterations', help="number of iterations to run",type=int)
    args = parser.parse_args()

    times=[]
    import time
    for i in range(args.iterations):
        start = time.perf_counter()
        if args.graph=='custom':
            import graph
            graph.runner(stream = False,query = args.query,render = False)
        elif args.graph=='prebuilt':
            prebuilt_runner(args.query)
        else:
            print(f"Invalid choice of {args.graph}")
            sys.exit(1)
        end = time.perf_counter()
        elapsed = end-start
        if i>=args.warmupsteps:
            times.append(elapsed)
    mean_time = sum(times)/len(times)
    print(f"Elapsed times are {times}")
    print(f"Mean run time for {args.graph} was {mean_time:.2f}")




if __name__ == "__main__":
    main()
