"""
Conditional Workflow Agent - Dynamic Routing

Demonstrates a conditional workflow where a router agent analyzes the input
and delegates to the appropriate specialist agent based on the task type.

Pattern: User Input → Router (classifies) → Specialist Agent → Response

Prerequisites:
    pip install -r requirements.txt

Learning objectives:
- Understand dynamic agent routing and task classification
- See how to build a dispatcher that selects the right specialist
- Learn conditional branching in multi-agent workflows
- Practice designing specialized agents for different domains
"""

import sys
import time
from shared.model import get_model
from shared.input_utils import get_multiline_input
from shared.streaming import StreamingCallbackHandler
from strands import Agent


# --- Specialist Agents ---
#
# Each specialist gets its own streaming handler so its response shows up
# live below the router's classification line. The router itself stays
# silent — it just emits a one-word category, so the spinner UI is a better
# fit than streaming a single token.

code_handler = StreamingCallbackHandler()
writing_handler = StreamingCallbackHandler()
analysis_handler = StreamingCallbackHandler()
math_handler = StreamingCallbackHandler()

code_agent = Agent(
    model=get_model(),
    system_prompt="""You are a Code Assistant specializing in software development.

When given a coding task:
1. Understand the requirements clearly
2. Write clean, well-documented code
3. Include error handling
4. Explain your implementation choices

You handle: code generation, debugging, code review, refactoring, and technical questions.
Use Python unless another language is specified.""",
    callback_handler=code_handler,
)

writing_agent = Agent(
    model=get_model(),
    system_prompt="""You are a Writing Assistant specializing in content creation.

When given a writing task:
1. Understand the audience and purpose
2. Use clear, engaging language
3. Structure content logically
4. Maintain consistent tone throughout

You handle: emails, blog posts, documentation, summaries, creative writing, and editing.""",
    callback_handler=writing_handler,
)

analysis_agent = Agent(
    model=get_model(),
    system_prompt="""You are a Data Analysis Assistant specializing in reasoning about information.

When given an analysis task:
1. Break down the problem systematically
2. Consider multiple perspectives
3. Support conclusions with evidence
4. Present findings clearly

You handle: comparisons, evaluations, research questions, pros/cons analysis, and strategic thinking.""",
    callback_handler=analysis_handler,
)

math_agent = Agent(
    model=get_model(),
    system_prompt="""You are a Math and Calculation Assistant.

When given a math problem:
1. Identify what's being asked
2. Show your work step by step
3. Verify your answer
4. Explain the approach used

You handle: arithmetic, algebra, statistics, word problems, unit conversions, and financial calculations.""",
    callback_handler=math_handler,
)


# --- Router Agent ---

ROUTER_PROMPT = """You are a Task Router. Your ONLY job is to classify the user's request
into exactly one category. Do not answer the question yourself.

Categories:
- CODE: Programming, debugging, code review, technical implementation
- WRITING: Emails, blog posts, documentation, creative writing, editing
- ANALYSIS: Research, comparisons, evaluations, strategic questions, pros/cons
- MATH: Calculations, arithmetic, statistics, word problems, conversions

Respond with ONLY the category name (CODE, WRITING, ANALYSIS, or MATH).
Nothing else. Just the single word."""

router_agent = Agent(
    model=get_model(),
    system_prompt=ROUTER_PROMPT,
    callback_handler=None,
)


# Map categories to specialist agents + their stream handlers
SPECIALISTS = {
    "CODE": ("Code Assistant", code_agent, code_handler),
    "WRITING": ("Writing Assistant", writing_agent, writing_handler),
    "ANALYSIS": ("Analysis Assistant", analysis_agent, analysis_handler),
    "MATH": ("Math Assistant", math_agent, math_handler),
}


def classify_task(user_input: str) -> str:
    """Use the router agent to classify the task type."""
    response = str(router_agent(user_input)).strip().upper()

    # Extract the category from the response (handle verbose responses)
    for category in SPECIALISTS:
        if category in response:
            return category

    # Default to analysis if classification is unclear
    return "ANALYSIS"


def run_conditional_workflow(user_input: str) -> None:
    """Execute the conditional workflow with streamed output.

    Pipeline: User Input → Router (classifies) → Specialist (streams) → Done
    """
    # Step 1: Classify the task — router is a single-word classifier, so the
    # spinner UI fits better than streaming a single token.
    print(f"    ⟳ {'Router':<12} classifying...")
    step_start = time.time()
    category = classify_task(user_input)
    specialist_name, specialist_agent, specialist_handler = SPECIALISTS[category]
    duration = time.time() - step_start
    sys.stdout.write("\033[1A")
    sys.stdout.write(
        f"\r    ✓ {'Router':<12} → {specialist_name} ({duration:.1f}s)\033[K\n"
    )
    sys.stdout.flush()

    # Step 2: Delegate to specialist — streams its response live.
    print(f"\n  ─── {specialist_name} ───\n")
    specialist_handler.reset()
    step_start = time.time()
    specialist_agent(user_input)
    duration = time.time() - step_start
    print(f"\n  ✓ {specialist_name} complete ({duration:.1f}s)")


def main():
    """Run the conditional workflow agent interactively."""
    print("Conditional Workflow Agent")
    print("=" * 40)
    print("A router classifies your request and delegates to the right specialist:")
    print("  • Code Assistant — programming and technical tasks")
    print("  • Writing Assistant — content creation and editing")
    print("  • Analysis Assistant — research and evaluation")
    print("  • Math Assistant — calculations and word problems")
    print("Type 'quit' to exit")
    print("Tip: You can paste multi-line prompts!\n")

    print("Example prompts to try:")
    print("  - Write a Python function to validate email addresses")
    print("  - Draft a professional email declining a meeting invitation")
    print("  - Compare AWS Lambda vs ECS Fargate for a REST API")
    print("  - If I invest $10,000 at 7% annual return, what's it worth in 20 years?\n")

    while True:
        user_input = get_multiline_input("You: ").strip()

        if user_input.lower() in ["quit", "exit", "q"]:
            print("Goodbye!")
            break

        if not user_input:
            continue

        try:
            print()
            start_time = time.time()
            run_conditional_workflow(user_input)
            total_time = time.time() - start_time
            print(f"\n  Total time: {total_time:.1f}s\n")
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()
