import asyncio
import os
import sys

from google.adk.agents import Agent, SequentialAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

# Import core tools and orchestration patterns
from i18n_agent_skill.tools import (
    extract_raw_strings,
    load_project_glossary,
    propose_sync_i18n,
)

# Validate API Key
if not os.environ.get("GOOGLE_API_KEY"):
    print("\033[91mError: GOOGLE_API_KEY is not set.\033[0m")
    sys.exit(1)

# Define Agent orchestration workflow
workflow = SequentialAgent(
    name="I18nWorkflowAgent",
    agents=[
        Agent(
            name="GlossaryLoader",
            tools=[load_project_glossary],
            instructions="Load project glossary to ensure translation consistency.",
        ),
        Agent(
            name="ContextAwareExtractor",
            tools=[extract_raw_strings],
            instructions="Extract UI text and its context.",
        ),
        Agent(
            name="Proposer",
            tools=[propose_sync_i18n],
            instructions="""
            Generate a change proposal. You must state the decision basis in the reasoning field:
            1. Did you refer to the glossary?
            2. How did the code context snippets affect the translation choice?
            """,
        ),
    ],
)


async def run_example():
    runner = Runner(agent=workflow, session_service=InMemorySessionService())

    print("🚀 Starting automated i18n workflow...")

    # Simulated run
    result = await runner.run(
        session_id="i18n_task_001",
        user_input=(
            "Sync src/ui/Header.js. Please use the glossary "
            "to ensure consistent translation of 'Submit'."
        ),
    )

    print("\n" + "=" * 50)
    print("Agent Proposal (with Reasoning):")
    print("=" * 50)
    print(result.text)


if __name__ == "__main__":
    asyncio.run(run_example())
