"""
Sequential Workflow Agent - Multi-Agent Pipeline

Demonstrates a sequential workflow where multiple specialized agents
work in series: each agent's output feeds into the next agent's input.

Pattern: Researcher → Analyst → Writer

Each stage streams its work live so the viewer can see what every
specialist actually contributes, rather than only seeing the final
report.

Prerequisites:
    pip install -r requirements.txt

Learning objectives:
- Understand sequential agent-to-agent communication
- See how to decompose complex tasks into specialized roles
- Watch each stage stream its reasoning in real time
"""

import ipaddress
import socket
import time
from urllib.parse import urljoin, urlparse
from shared.model import get_model
from shared.input_utils import get_multiline_input
from shared.streaming import StreamingCallbackHandler
from strands import Agent, tool
import requests


def _resolves_to_blocked_ip(host: str) -> bool:
    """True if ``host`` resolves to a non-public IP (private, loopback, etc.).

    Used for SSRF protection so an LLM-chosen URL can never reach an
    internal-only address.
    """
    try:
        addrinfo = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return True  # unresolvable -> refuse
    for *_, sockaddr in addrinfo:
        ip = ipaddress.ip_address(sockaddr[0])
        if (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
            return True
    return False


@tool
def http_request(url: str, method: str = "GET") -> str:
    """Make an HTTP request to retrieve information from the web.

    Args:
        url: The URL to request
        method: HTTP method (GET, POST)
    """
    print(f"          http_request(url={url!r}, method={method!r})")

    # --- SSRF protection ---------------------------------------------------
    # This tool fetches URLs the LLM chooses, which can be influenced by user
    # input via prompt injection. Left open, an agent could be steered into
    # requesting internal-only resources — most dangerously the cloud instance
    # metadata endpoint (169.254.169.254 / fd00:ec2::254), which on a deployed
    # host can leak credentials, or other services on the private network.
    # Defenses (see AWS BSC12 SSRF guidance):
    #   1. Only http/https, with a real host.
    #   2. Restrict the HTTP method to GET/POST.
    #   3. Resolve the host and refuse any non-public (private/loopback/
    #      link-local/reserved) address — this blocks the metadata endpoint.
    #   4. Follow redirects manually, re-validating every hop, so a public URL
    #      can't 3xx-bounce us onto an internal address.
    # NOTE: resolve-then-request leaves a small DNS-rebinding (TOCTOU) window;
    # pinning the resolved IP for the connection closes it fully but is beyond
    # this teaching example.
    if method.upper() not in ("GET", "POST"):
        result = f"Blocked method {method!r}. Only GET and POST are allowed."
        print(f"          -> {result}")
        return result

    MAX_REDIRECTS = 5
    current_url = url
    try:
        for _ in range(MAX_REDIRECTS + 1):
            parsed = urlparse(current_url)
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                result = f"Invalid URL: {current_url!r}. Must be an http:// or https:// address."
                print(f"          -> {result}")
                return result

            host = parsed.hostname
            if not host or _resolves_to_blocked_ip(host):
                result = (f"Blocked URL: {current_url!r} — refused to prevent SSRF "
                          f"(host is missing or resolves to a private/internal address).")
                print(f"          -> {result}")
                return result

            # allow_redirects=False so we can re-run the SSRF check on each hop
            # ourselves rather than letting requests follow blindly.
            response = requests.request(method, current_url, timeout=10, allow_redirects=False)
            if response.is_redirect:
                location = response.headers.get("Location")
                if not location:
                    break
                current_url = urljoin(current_url, location)  # resolve relative redirects
                continue

            response.raise_for_status()
            body = response.text[:3000]
            print(f"          -> {response.status_code} ({len(body)} chars returned)")
            return body

        result = f"Too many redirects (> {MAX_REDIRECTS}) starting from {url!r}."
        print(f"          -> {result}")
        return result
    except Exception as e:
        result = f"Request failed: {e}"
        print(f"          -> {result}")
        return result


# --- Streaming handlers (one per agent so they can be reset independently) ---

researcher_handler = StreamingCallbackHandler()
analyst_handler = StreamingCallbackHandler()
writer_handler = StreamingCallbackHandler()


# --- Agent Definitions ---

researcher_agent = Agent(
    model=get_model(),
    system_prompt="""You are a Researcher Agent that gathers information from the web.

When given a topic:
1. Use the http_request tool to find relevant information
2. Summarize your findings clearly
3. Include source URLs when available
4. Keep findings under 500 words

Focus on factual, verifiable information from reliable sources.""",
    tools=[http_request],
    callback_handler=researcher_handler,
)

analyst_agent = Agent(
    model=get_model(),
    system_prompt="""You are an Analyst Agent that evaluates research findings.

When given research findings:
1. Identify the 3-5 most important insights
2. Evaluate the reliability of the sources
3. Note any gaps or contradictions in the information
4. Rate confidence level (high/medium/low) for each insight
5. Keep analysis under 400 words

Be critical and objective in your assessment.""",
    callback_handler=analyst_handler,
)

writer_agent = Agent(
    model=get_model(),
    system_prompt="""You are a Writer Agent that creates clear, structured reports.

When given analysis:
1. Create a well-organized report with clear sections
2. Lead with the most important findings
3. Use plain language accessible to a general audience
4. Include a brief conclusion with actionable takeaways
5. Keep the report under 500 words

Write in a professional but approachable tone.""",
    callback_handler=writer_handler,
)


def _run_stage(name: str, agent: Agent, handler: StreamingCallbackHandler, prompt: str) -> str:
    """Run one stage of the pipeline with streamed output and timing."""
    print(f"\n  ─── {name} ───\n")
    handler.reset()
    start = time.time()
    response = agent(prompt)
    duration = time.time() - start
    print(f"\n  ✓ {name} complete ({duration:.1f}s)")
    return str(response)


def run_sequential_workflow(user_input: str) -> None:
    """Execute the three-agent sequential workflow with streamed output.

    Pipeline: User Input → Researcher → Analyst → Writer → Final Report

    Each stage streams its output to stdout. There is no separate final
    report block — the Writer's streamed output IS the final report.
    """
    research_findings = _run_stage(
        "Researcher",
        researcher_agent,
        researcher_handler,
        f"Research the following topic thoroughly: '{user_input}'",
    )

    analysis = _run_stage(
        "Analyst",
        analyst_agent,
        analyst_handler,
        f"Analyze these research findings about '{user_input}':\n\n{research_findings}",
    )

    _run_stage(
        "Writer",
        writer_agent,
        writer_handler,
        f"Create a report on '{user_input}' based on this analysis:\n\n{analysis}",
    )


def main():
    """Run the sequential workflow agent interactively."""
    print("Sequential Workflow Agent")
    print("=" * 40)
    print("A three-agent pipeline: Researcher → Analyst → Writer")
    print("Give me a topic and I'll research, analyze, and write a report.")
    print("Each stage streams live so you can watch its contribution.")
    print("Type 'quit' to exit")
    print("Tip: You can paste multi-line prompts!\n")

    print("Example prompts to try:")
    print("  - What are the latest developments in quantum computing?")
    print("  - Compare serverless vs container architectures for microservices")
    print("  - What is retrieval-augmented generation and why does it matter?\n")

    while True:
        user_input = get_multiline_input("You: ").strip()

        if user_input.lower() in ["quit", "exit", "q"]:
            print("Goodbye!")
            break

        if not user_input:
            continue

        try:
            print(f"\nProcessing: '{user_input[:60]}...'")
            start_time = time.time()
            run_sequential_workflow(user_input)
            total_time = time.time() - start_time
            print(f"\n{'=' * 40}")
            print(f"PIPELINE COMPLETE ({total_time:.1f}s)")
            print(f"{'=' * 40}\n")
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()
