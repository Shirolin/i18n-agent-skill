import asyncio
from i18n_agent_skill.tools import _detect_locale_dir

async def main():
    print("i18n-agent-skill CLI Tool")
    print("-" * 30)
    detected_dir = _detect_locale_dir()
    print(f"Detected locale directory: {detected_dir}")
    print("Run 'python -m examples.basic_usage' to see a full agent workflow example.")

if __name__ == "__main__":
    asyncio.run(main())
