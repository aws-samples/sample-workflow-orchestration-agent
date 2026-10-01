# Orchestrating Agents: Sequential, Parallel, and Conditional Workflows

*Break a complex task into stages and assign each to a specialized agent*

---

This is the seventh post in our series on [AWS Prescriptive Guidance for Agentic AI Patterns](https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-patterns/). Each post focuses on the concepts and patterns behind a single agent type, paired with a [hands-on sample on GitHub](README.md).

## Introduction

Every agent in this series so far has worked solo, whether it was reasoning, calling tools, or (in the [previous post](https://github.com/aws-samples/sample-speech-voice-agents/blob/main/Giving%20Agents%20a%20Voice%20-%20Speech-to-Speech%20and%20the%20STT-TTS%20Pipeline.md)) holding a spoken conversation. That's fine for focused tasks, but complex work has structure: research *then* analyze *then* write; gather several perspectives *and then* reconcile them; figure out *what kind* of request this is before answering it.

A workflow orchestration agent imposes that structure. Instead of one agent trying to do everything in a single prompt, an orchestrator breaks the task into stages, assigns each to a specialized agent, tracks the state between them, and adapts based on what comes back. When the work genuinely has that shape, each agent ends up with one clear job. This makes the system easier to inspect at each step allowing you to improve a piece at a time and debug when something goes wrong

By the end of this post, you'll understand:
- Why decomposing a task across agents might win over one large prompt
- The three foundational orchestration patterns: sequential, parallel, and conditional
- How orchestration relates to managed services like AWS Step Functions
- When to orchestrate, and when a single agent is enough

---

## The Road to Orchestration: A Brief History

Coordinating many steps into one reliable process is an old discipline and agents are the newest thing being coordinated.

### Workflow engines and BPM

Companies define and run multistep processes through workflow engines and business process management (BPM) systems. These defined steps, transitions, and error handling explicitly. Every branch had to be drawn in advance.

### Serverless orchestration

Cloud orchestration made those workflows elastic and event-driven. [AWS Step Functions](https://aws.amazon.com/step-functions/), for example, coordinates distributed components as state machines by sequencing tasks and running them in parallel without managing servers.

### Orchestrating agents

What's new is that the units being coordinated are now LLM-powered agents, and the orchestrator can itself reason. Rather than a fixed decision tree, an orchestrator can use an LLM to *select* which agent should handle a task and to compose prompts for it on the fly. Frameworks like the [Strands Agents SDK](https://strandsagents.com/) make agents into reusable building blocks so the same sequence/parallel/branch shapes now apply to teams of agents.

---

## Why Decompose at All

The instinct is often to make one agent smarter with more context and tools. That hits limits fast: a single prompt juggling research *and* analysis *and* writing might perform each job worse than three focused agents. Each task competes for the model's attention and context, and becomes hard to debug when the output is wrong.

Decomposition helps frame the problem in the same way that ordinary software does. Each agent has a single responsibility and a prompt tuned for exactly that job. You can inspect the output at each stage, swap or improve one agent without touching the others, and reason about failures locally. The orchestrator's job is to move work between these specialists and hold the state that connects them.

---

## Three Foundational Patterns

<img src="images/workflow-orchestration-agents.png" width="600" alt="Diagram of a workflow orchestration agent: user input triggers an orchestrator that retrieves context, selects worker agents, and delegates work to them in sequence, tracking state and passing intermediate results." />

Almost any agent workflow is built from three patterns, alone or combined.

| Pattern | Flow | Use when |
|-------|------|----------|
| **Sequential** | A → B → C, each output feeds the next | Stages depend on each other |
| **Parallel** | A, B, C at once → merge | Subtasks are independent |
| **Conditional** | Router → the right specialist | Different request types need different expertise |

A **sequential** pipeline chains stages where a researcher's findings feed an analyst, whose assessment feeds a writer; each stage depends on the one before. **Parallel** fans out the same input out to independent specialists and synthesizes their results. **Conditional** puts a lightweight classifier in front and dispatches to the matching specialist; a coding question and a writing request take entirely different paths.

These three can be combined. A real system might route conditionally to a branch that runs several agents in parallel and then pipes the merged result through a sequential review, but every piece is one of these three.

---

## Orchestration in Code vs. Managed Services

At enterprise scale, you often want the orchestration itself to be durable, observable, and resilient to failure. [AWS Step Functions](https://aws.amazon.com/step-functions/) gives you state machines with built-in retries, parallel branches, and audit trails; [Amazon EventBridge](https://aws.amazon.com/eventbridge/) decouples agents through events so they can run asynchronously and independently. The patterns are identical with sequence, parallel, and choice, but the runtime handles state, retries, and recovery so you don't have to.

The trade-off is the usual one. Plain code is transparent and trivial to change. A managed orchestrator earns its added complexity when failures are expensive, runs are long, or you need an audit trail of exactly which agent did what.

---

## When to Use Workflow Orchestration

Orchestrate when a task has real structure or independent parts.

| Use Case | Example |
|----------|---------|
| **Multistep automation** | Data ingestion, then analysis, then reporting |
| **Service routing & escalation** | An agent-as-coordinator dispatching support requests |
| **Human + bot loops** | AI agents and people collaborating in one process |
| **Enterprise process automation** | LLM-powered logic driving existing business processes |
| **Hybrid systems** | Combining AI agents with traditional orchestration tools |

### When a Single Agent Is Enough

Orchestration adds moving parts. For a focused task that one well-prompted agent handles cleanly, that overhead is pure cost. Decompose when the task genuinely has stages or independent subtasks, or when one prompt has grown so crowded it's doing several jobs badly. If a single agent does the job well, keep it. We'll dive deeper into the tradeoffs in the [eleventh](https://github.com/aws-samples/sample-multi-agent-collaboration/blob/main/When%20Multi-Agent%20Collaboration%20Earns%20Its%20Cost.md) part of this series.

---

## What's Next

You now understand why decomposing work across agents beats one over-stuffed prompt, the three foundational orchestration patterns, and how they map to managed services. The natural next step is to see them run. The **[companion sample](README.md)** builds sequential, parallel, and conditional workflows, with live status output so you can watch the coordination.

Orchestration coordinates agents, but each agent still forgets everything between sessions. In the [next post](https://github.com/aws-samples/sample-memory-augmented-agents/blob/main/Agents%20That%20Remember%20-%20Context%20Windows%2C%20Summaries%2C%20and%20Persistent%20Sessions.md), we'll give agents memory using sliding windows, summarization, and persistent sessions.

---

## Resources

- [Companion sample: Workflow Orchestration Agents](README.md)
- [AWS Prescriptive Guidance - Workflow orchestration agents](https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-patterns/workflow-orchestration-agents.html)
- [AWS Step Functions](https://aws.amazon.com/step-functions/)
- [Strands Agents Documentation](https://strandsagents.com/)
- [Amazon Bedrock User Guide](https://docs.aws.amazon.com/bedrock/latest/userguide/what-is-bedrock.html)

---

**Tim Sitze** is a Solutions Architect at Amazon Web Services, where he works with cybersecurity ISVs to design and scale their products on AWS. He specializes in security, AI/ML, IoT and data platform architectures, and has partnered on workloads spanning identity threat intelligence, agentic AI, and cloud-native security operations. Tim is based in the Washington, D.C. area.  
