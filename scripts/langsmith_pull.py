import os
import json
import argparse
from dotenv import load_dotenv

from langsmith import Client
from langchain_core.load import dumpd

# Load environment variables
load_dotenv(".env.local", override=False)
load_dotenv(".env", override=False)

def pull_langsmith_prompt(prompt_name: str, output_file: str):
    print(f"Fetching prompt '{prompt_name}' from LangSmith...")
    
    client = Client()
    try:
        # Added secrets_from_env=True to allow the model to see your API Key
        prompt = client.pull_prompt(
            prompt_name,
            include_model=True,
            secrets_from_env=True  # Essential for langsmith >= 0.5.1
        )

        print("\n✅ Prompt fetched successfully.")
        print(f"Object type: {type(prompt)}")

        # Logic to handle both raw prompts and sequences
        if hasattr(prompt, "messages"):
            # This is a raw PromptTemplate
            print(f"Number of messages: {len(prompt.messages)}")
        elif hasattr(prompt, "first"):
            # This is a RunnableSequence (Prompt + Model)
            if hasattr(prompt.first, "messages"):
                print(f"Number of messages in sequence: {len(prompt.first.messages)}")
            print(f"Model step: {prompt.last}")

        # Save to file
        with open(output_file, "w") as file:
            # dumpd converts the LangChain object into a JSON-serializable dict
            serializable_prompt = dumpd(prompt)
            json.dump(serializable_prompt, file, indent=2)
            
        print(f"✅ Prompt saved to {output_file}")
        return prompt

    except Exception as e:
        print(f"\n❌ Failed to pull prompt: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Pull a prompt from LangSmith and save it as JSON.")
    parser.add_argument(
        "--prompt", 
        type=str, 
        default="kingseno49/system_prompt:staging",
        help="The name of the prompt to pull (e.g., 'kingseno49/system_prompt:staging')"
    )
    parser.add_argument(
        "--output", 
        type=str, 
        default="prompt.json",
        help="The output JSON file path"
    )
    args = parser.parse_args()

    pull_langsmith_prompt(args.prompt, args.output)

if __name__ == "__main__":
    main()
