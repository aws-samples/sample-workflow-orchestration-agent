"""
Parallel Workflow Agent - Concurrent Multi-Agent Execution

Demonstrates a parallel workflow where multiple agents work simultaneously
on different aspects of the same task, then results are merged by a
synthesizer agent.

Pattern: User Input → [Agent A, Agent B, Agent C] (parallel) → Synthesizer

Prerequisites:
    pip install -r requirements.txt

Learning objectives:
- Understand parallel agent execution patterns
- See how to split tasks across specialized agents
- Learn to aggregate results from concurrent agents
- Compare parallel vs sequential performance
"""

import sys
import asyncio
import time
from shared.model import get_model
from shared.input_utils import get_multiline_input
from shared.streaming import StreamingCallbackHandler
from strands import Agent


# --- Specialized Parallel Agents ---
#
# These three agents run concurrently. Streaming their token-level output
# to a single stdout would interleave into nonsense, so we leave them with
# `callback_handler=None` and rely on the status-line UI below to surface
# progress. The synthesizer agent further down DOES stream — it runs alone
# after the parallel phase, so its output reads cleanly.

technical_agent = Agent(
    model=get_model(),
    system_prompt="""You are a Technical Analysis Agent.

When given a topic, analyze it from a purely technical perspective:
1. How does the technology work?
2. What are the technical advantages and limitations?
3. What are the implementation challenges?

Keep your analysis under 300 words. Be specific and technical.""",
    callback_handler=None,
)

business_agent = Agent(
    model=get_model(),
    system_prompt="""You are a Business Impact Agent.

When given a topic, analyze it from a business perspective:
1. What business problems does it solve?
2. What is the cost/benefit analysis?
3. Who are the key players and what's the market landscape?

Keep your analysis under 300 words. Focus on practical business value.""",
    callback_handler=None,
)

risk_agent = Agent(
    model=get_model(),
    system_prompt="""You are a Risk Assessment Agent.

When given a topic, analyze potential risks and challenges:
1. What could go wrong?
2. What are the security or compliance concerns?
3. What are the adoption barriers?

Keep your analysis under 300 words. Be thorough but realistic.""",
    callback_handler=None,
)

synthesizer_handler = StreamingCallbackHandler()

synthesizer_agent = Agent(
    model=get_model(),
    system_prompt="""You are a Synthesis Agent that combines multiple analyses into a cohesive summary.

When given technical, business, and risk analyses:
1. Identify the key themes across all three perspectives
2. Highlight areas of agreement and tension
3. Provide a balanced recommendation
4. Keep the synthesis under 400 words

Create a unified view that helps decision-makers understand the full picture.""",
    callback_handler=synthesizer_handler,
)


# Serializes terminal writes when multiple agents complete concurrently.
_DISPLAY_LOCK = asyncio.Lock()


async def run_agent_async(agent: Agent, prompt: str, name: str, line_offset: int, total_lines: int) -> str:
    """Run an agent asynchronously and update its status line in place."""
    start = time.time()
    response = await agent.invoke_async(prompt)
    duration = time.time() - start

    # Serialize terminal writes so concurrent completions don't corrupt the display.
    async with _DISPLAY_LOCK:
        # Move cursor up to this agent's line, overwrite it, then move back down
        lines_up = total_lines - line_offset
        sys.stdout.write(f"\033[{lines_up}A")  # Move up
        sys.stdout.write(f"\r    ✓ {name:<18} complete ({duration:.1f}s)\033[K\n")  # Overwrite
        sys.stdout.write(f"\033[{lines_up - 1}B")  # Move back down
        sys.stdout.flush()

    return str(response)


async def run_parallel_agents(user_input: str) -> dict:
    """Run three analysis agents in parallel with live status updates."""
    prompt_template = f"Analyze this topic from your perspective: '{user_input}'"

    agents = [
        ("Technical Agent", technical_agent),
        ("Business Agent", business_agent),
        ("Risk Agent", risk_agent),
    ]

    # Print initial status lines
    for name, _ in agents:
        print(f"    ⟳ {name:<18} running...")

    # Launch all agents concurrently
    total_lines = len(agents)
    results = await asyncio.gather(*[
        run_agent_async(agent, prompt_template, name, idx, total_lines)
        for idx, (name, agent) in enumerate(agents)
    ])

    return {
        "technical": results[0],
        "business": results[1],
        "risk": results[2],
    }


def run_parallel_workflow(user_input: str) -> None:
    """Execute the parallel workflow with synthesis.

    Pipeline: User Input → [Technical, Business, Risk] (parallel) → Synthesizer

    Parallel agents use status lines (their concurrent output would interleave
    if streamed). The synthesizer streams normally since it runs alone.
    """
    print("  Running 3 agents in parallel...\n")
    start_time = time.time()

    # Run parallel agents (status lines update in place)
    results = asyncio.run(run_parallel_agents(user_input))
    parallel_time = time.time() - start_time
    print(f"\n  All agents complete ({parallel_time:.1f}s)")

    # Synthesize results — streamed since it runs alone
    print("\n  ─── Synthesizer ───\n")
    synth_start = time.time()
    synthesis_prompt = (
        f"Synthesize these three analyses about '{user_input}':\n\n"
        f"TECHNICAL ANALYSIS:\n{results['technical']}\n\n"
        f"BUSINESS ANALYSIS:\n{results['business']}\n\n"
        f"RISK ASSESSMENT:\n{results['risk']}\n\n"
        "Create a unified summary with a clear recommendation."
    )

    synthesizer_handler.reset()
    synthesizer_agent(synthesis_prompt)
    print(f"\n  ✓ Synthesizer complete ({time.time() - synth_start:.1f}s)")
    total_time = time.time() - start_time
    print(f"  Total workflow time: {total_time:.1f}s\n")


def main():
    """Run the parallel workflow agent interactively."""
    print("Parallel Workflow Agent")
    print("=" * 40)
    print("Three agents analyze your topic simultaneously from different angles:")
    print("  • Technical Agent — how it works")
    print("  • Business Agent — why it matters")
    print("  • Risk Agent — what could go wrong")
    print("Then a Synthesizer combines their insights into one report.")
    print("Type 'quit' to exit")
    print("Tip: You can paste multi-line prompts!\n")

    print("Example prompts to try:")
    print("  - Should we adopt generative AI for customer support?")
    print("  - Evaluate migrating our monolith to microservices")
    print("  - Is serverless the right choice for our real-time data pipeline?\n")

    while True:
        user_input = get_multiline_input("You: ").strip()

        if user_input.lower() in ["quit", "exit", "q"]:
            print("Goodbye!")
            break

        if not user_input:
            continue

        try:
            print(f"\nAnalyzing: '{user_input[:60]}...'\n")
            run_parallel_workflow(user_input)
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()
