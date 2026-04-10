# Claude Code Architecture & Memory System

## 1. The 3-Layer Memory System
Claude Code utilizes a structured, hierarchical memory system to manage context effectively without overflowing the LLM window.
* **Layer 1 - Index:** A high-level directory of all known information. The agent queries this first to decide which specific topics to load.
* **Layer 2 - Topic Files:** Granular, subject-specific files containing condensed, structured knowledge about particular domains or codebase sections.
* **Layer 3 - Session Transcripts:** The raw timeline of user interactions, tool calls, and execution results for the current session.

## 2. autoDream Memory Consolidation
Instead of carrying all past conversations forever, the agent uses a background compaction process known as `autoDream`. 
* When a session concludes or context grows too large, `autoDream` summarizes the raw session transcripts (Layer 3).
* It extracts reusable facts, corrected mistakes, and successful patterns, compressing them and saving them into the relevant Topic Files (Layer 2).
* This provides a continuous learning loop without monolithic context bloat.

## 3. Tool Scoping Philosophy
Claude Code avoids monolithic, "do-everything" tools.
* Tools have extremely tight domain boundaries and single responsibilities (e.g., over 40+ specific tools).
* This ensures that execution failures are isolated and the agent can easily diagnose exactly which step of a complex operation failed.
