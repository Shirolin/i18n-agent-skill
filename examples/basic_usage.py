import asyncio
import os
import sys
import json
from google.adk.agents import Agent, SequentialAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

# 引入核心工具与大师级范式
from i18n_agent_skill.tools import (
    extract_raw_strings, propose_sync_i18n, commit_i18n_changes, load_project_glossary
)
from i18n_agent_skill.models import ConflictStrategy

# 校验 API Key
if not os.environ.get("GOOGLE_API_KEY"):
    print("\033[91mError: GOOGLE_API_KEY is not set.\033[0m")
    sys.exit(1)

# 定义一个大师级 Agent 编排
workflow = SequentialAgent(
    name="MasterI18nAgent",
    agents=[
        Agent(
            name="GlossaryLoader",
            tools=[load_project_glossary],
            instructions="首先加载项目术语表，确保翻译一致性。"
        ),
        Agent(
            name="ContextAwareExtractor", 
            tools=[extract_raw_strings], 
            instructions="提取 UI 文本及其上下文。利用 context 区分词义。"
        ),
        Agent(
            name="TraceableProposer", 
            tools=[propose_sync_i18n], 
            instructions="""
            生成变更提案。你必须在 reasoning 字段中写明决策依据：
            1. 是否参考了术语表？
            2. 上下文代码片段是如何影响你的翻译选择的？
            """
        )
    ]
)

async def run_master_example():
    runner = Runner(agent=workflow, session_service=InMemorySessionService())
    
    print("🚀 启动大师级可追溯国际化工作流...")
    
    # 模拟运行
    result = await runner.run(
        session_id="master_task_001",
        user_input="同步 src/ui/Header.js。请使用术语表确保 'Submit' 被统一翻译为业务要求的词汇。"
    )
    
    print("\n" + "="*50)
    print("Agent Master Proposal (with Reasoning):")
    print("="*50)
    print(result.text)

if __name__ == "__main__":
    asyncio.run(run_master_example())
