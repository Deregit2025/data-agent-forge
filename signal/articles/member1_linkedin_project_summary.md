# From 1.85% to 44.4%: The Full Story of How Team Gemini Built a Self-Learning Data Agent in a Two-Week Sprint

*Author: Rafia Kedir  & Nuhamin Alemayehu— Team Gemini / Oracle Forge*

---

## Published on

| Platform | URL | Date |
|----------|-----|------|
| LinkedIn | https://www.linkedin.com/pulse/from-185-444-full-story-how-team-gemini-built-data-agent-alemayehu-ea5we | 2026-04-18 |

---

## Article text

April 18, 2026

Two weeks ago, our team embarked on an ambitioius mission, to beat Gemini Pro's 38% DAB ceiling via multi-layer context. Today, we submitted the result. Our story has near-catastrophic failure, relentless perseverance, and a breakthrough success that encapsulates the very essence of agile AI development.

Here is the detailed story of Oracle Forge, our production-grade, multi-database AI agent, and how we conquered the University of California, Berkeley's formidable DataAgentBench (DAB) challenge.

The Arena: What is the DataAgentBench (DAB) Challenge?
The DataAgentBench benchamark challenge was a crucible designed to test the limits of AI agents in a real-world scenario. The agents are expected to answer complex questions by querying unfamiliar databases. The challenge comprises 12 distinct datasets across four different database systems (PostgreSQL, MongoDB, SQLite, and DuckDB).

The metric for success is pass@1, which measures whether the agent can produce the correct answer on its first attempt. The bar was set high, we had to beat the 38% pass@1 score achieved by Gemini 3 Pro. Our mission was to build an agent that could not only meet but significantly exceed this benchmark.

Our Battle Plan: Compound Engineering and the Three-Unit Team
To tackle this complexity, we adopted the AI Development Lifecycle (AI-DLC) framework, but our core philosophy was a principle we call "Compound Engineering." In compound enginneering, the output from one unit had to be a trusted, high-quality, and immediately usable input for the next. The work of the Intelligence Officers in curating a knowledge base was a verifiable input that the Drivers' code could depend on. This eliminated rework and created a powerful multiplier effect, allowing us to build on each other's work with speed and confidence.

This philosophy was embodied in our team structure, where our six-person team, Team Gemini, was organized into three distinct, symbiotic units:

The Drivers ( Dereje Getie Eyoel Nebiyu ): Our drivers were the engineers with the hands-on-keyboard heart of the operation. They were responsible for the entire technical implementation of Oracle Forge. They wrote the Python code for the core conductor.py, engineered the specialized sub-agents for each of the four database types, and built the sophisticated self-correction engine. They were the ones in the trenches debugging code and who ultimately found and fixed the critical bug that turned our project around.
The Intelligence Officers ( Chalie Lijalem Liul Teshome ): The Strategists and brains behind the agent's knowledge. Our Intelligence Officers were tasked with deeply understanding the "why" behind the data.Inspired by Karpathy-style knowledge base principles, our IOs meticulously analyzed all 12 benchmark datasets, preparing the critical "Layer 2 Institutional Knowledge" that defines what abstract data means in reality (e.g., an "active customer" is one who purchased in the last 90 days). They developed our joint key glossary and the correction_logger function, forming the brain of our agent's learning capability.
The Signal Corps ( Rafia Kedir Nuhamin Alemayehu ): My team were the story tellers, responsible for building the bridge between our technical journey and the outside world. We documented every step of the sprint, managing our public-facing communications on X (@GeminiTrp1), Reddit, Medium, LinkedIn and Discord. Our mission was to translate the team's progress, struggles, and triumphs into a compelling narrative and compile the complete engagement log for our final submission.

Setback & Pivot: When Your Core Tooling Fails
Our initial plan was to leverage the recommended Google MCP Toolbox. However, we hit a wall very fast. The drivers discovered that the recommended v0.30.0 was insufficient as it didn't support DuckDB -- had a breaking change in flag syntax that caused silent failures-- and an older version only supported predefined queries. This was a critical moment. The pivot we made was building our own custom tools to handle the 9 DuckDB and 12 SQLite files, a decision that saved the project.

The Architecture of Success: How Oracle Forge Thinks and Learns
Inspired by deep dives into the ClaudeCode source leak and OpenAI's internal data agent papers, our success was engineered around a system built for resilience and learning.

The Three-Layer Context Architecture: Before the agent even attempts to write a query, the user's initial question is enriched by three powerful layers of context. This is our "secret sauce."

Layer 1 - Schema Layer: Provides the raw, structural map of the target database.
Layer 2 - Domain KB (Knowledge Base): A curated library of institutional knowledge.
Layer 3 - Corrections Memory: A dynamic, self-learning log where every corrected failure is stored, ensuring the agent learns from its mistakes.

2. The Conductor and Typed Failure Routing: The agent's core, orchestrated by conductor.py, uses a "plan -> fan-out -> merge" flow to run tasks in parallel. Crucially, we implemented typed failure routing. The agent identifies specific errors like JoinKeyMismatch or ContractViolation and triggers targeted recovery strategies instead of giving up.

All Hands on Deck: From 1.85% to a Team Breakthrough
Our initial tests were devastating, with a catastrophic 1.85% pass rate. The agent was failing. To diagnose the issue, we convened a full-team mob session, focusing all our energy on the complex Yelp dataset. There, we found and fixed a critical model ID bug, and in that single session, our pass rate on Yelp jumped from 1/7 to 4/7.

This was the validation we needed. With a proven strategy, we made a crucial decision for the final push: divide and conquer. Every single member of the team took ownership of two of the remaining datasets each, manually enriching the domain knowledge. We pooled our six individual API keys to accelerate our testing and began our final run.

The Final Results: Mission Accomplished
Today, we officially submitted our results to the UC Berkeley DataAgentBench leaderboard, and we are proud to share our final metrics.

🎯 Oracle Forge — DAB Benchmark Submission Complete

✅ Pass@1: 44.4% (24/54 queries passing)
✅ Above Baseline: Beats Gemini-3-Pro (38%) and the standalone Claude-Opus-4.6 model (43.8%).
✅ Total Runs: 270 (54 queries × 5 trials)
✅ Official PR: Submitted to the UC Berkeley DAB leaderboard: PR #32

🏆 Top Performing Datasets:

deps_dev: 100%
googlelocal: 75%
music_brainz: 67%
stockindex: 67%
stockmarket: 60%

Our final stack consists of LangGraph + Claude Sonnet 4.6, powered by a custom MCP server with 29 specialized tools and our core 3-layer Knowledge Base.

This two-week sprint proved that a disciplined framework, a dedicated team, and an architecture built for learning—combined with sheer grit and resourcefulness when faced with a deadline—can turn even the most daunting setbacks into incredible successes. A profound thank you to the entire Gemini team.

You can follow our entire journey on our GitHub: https://github.com/Deregit2025/data-agent-forge
