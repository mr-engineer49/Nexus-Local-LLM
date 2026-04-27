import os
import argparse
from typing import TypedDict
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END

# Load environment variables
load_dotenv(".env.local", override=False)
load_dotenv(".env", override=False)

# Define the state of your graph
class State(TypedDict):
    input: str
    output: str

# Define a simple node
def call_model(state: State):
    return {"output": f"Echo Agent Says: {state['input']}"}

def build_graph():
    """
    Builds and compiles the basic LangGraph.
    This can be imported and used elsewhere.
    """
    builder = StateGraph(State)
    builder.add_node("agent", call_model)
    builder.add_edge(START, "agent")
    builder.add_edge("agent", END)

    # This variable MUST match the name in your langgraph.json if used for deployment
    return builder.compile()

def run_agent(input_text: str):
    """
    Runs the input text through the graph.
    """
    print(f"🚀 Initializing graph with input: '{input_text}'")
    graph = build_graph()
    
    # Run the graph
    result = graph.invoke({"input": input_text})
    
    print("\n✅ Graph Execution Complete!")
    print(f"Resulting Output: {result.get('output', 'No output generated')}")
    return result

def main():
    parser = argparse.ArgumentParser(description="Run a basic LangGraph agent.")
    parser.add_argument(
        "--input", 
        type=str, 
        default="Hello LangGraph!",
        help="The input string to send to the agent"
    )
    args = parser.parse_args()

    run_agent(args.input)

if __name__ == "__main__":
    main()
