# Week 9 Slack Update

---

Nuhamin Alemayehu  [12:05 PM]
# Tuesday 14 April Mob Session 
Session led by Driver @Dereje Derib

**Shipped:**
The system runs End-to-end `Yelp` dataset  domain knowledge has been e nriched

**Learned:**
Our agents work well if we tweaked the domain knowledge context layer.

**Blockers:**
API key limitation.

**Next steps:**
Each of us will work on 2 datasets each and enrich the domain knowledge.

**Division of datasets:**
@Eyoel N. `agnews` and `bookreview`, @Chalie LIjalem `crmarenapro` and `deps_dev`, @Liul J. Teshome `github_repos` and `googlelocal`, @Nuhamin Alemayehu `music_brainz` and `pancancer`, @Rafia  `patents` and `stockindex`, @Dereje Derib `stockmarket` and `yelp`

The next mob session will be  on April 15 at 8 pm led by driver @Eyoel N.

---

Nuhamin Alemayehu  9:42 PM
https://www.reddit.com/r/learnmachinelearning/s/Fk2EyuBhEFReddit From the learnmachinelearning community on Reddit: Breaking the 38% Ceiling: How we hit a 57% pass rate on UC Berkeley’s DataAgentBench (Yelp Dataset)Explore this post and more from the learnmachinelearning communityhttps://www.reddit.com/r/learnmachinelearning/s/Fk2EyuBhEF

---

Nuhamin Alemayehu  [6:37 AM]
@channel Hey team, the agent is finally running from my side and I have started working on music_brainz dataset. I will update my progress in few hours. All queries in music_brainz and pancancer fail atm. Also @Rafia please update yesterday's mob session here on slack so it can be logged. (edited)

---

Rafia  [7:43 AM]
Daily Update

- Chalie – shared his progress
- Eyoel – still working on it(nothing new for today)
- Dereje – 4/7 tests passing (Yelp dataset), 3/5 passing (Stock Market dataset)

We still have 0 passing tests for the Patent and Book Review datasets.

We agreed to keep working on these and aim to make progress by midday. We’ll also be using all our API keys jointly moving forward.

Attendees: All members

---

Rafia  9:40 AM
Hey team I just drafted a LinkedIn post, any suggestions?
After two weeks of building, debugging, and benchmarking — Oracle Forge is being shipped.

Oracle Forge is a multi-database AI agent that answers natural language questions across PostgreSQL, MongoDB, SQLite, and DuckDB simultaneously. The hard part isn't query generation. It's context.

Enterprise data is fragmented, inconsistently keyed, and full of unstructured fields. Most agents fail silently on exactly that.

Our approach:
→ 3-layer context injection before every query (schema, domain knowledge, self-learned corrections)
→ LangGraph conductor that decomposes questions into per-database sub-tasks and merges results
→ Typed failure routing — JoinKeyMismatch, ContractViolation, DialectError — each with its own recovery protocol, not a generic retry
→ Evaluation harness that traces every tool call and scores against ground truth

The biggest lesson: we went from 1.85% → 66.7% on the yelp dataset with one KB update and a model ID fix. No architecture change. No prompt rewrite. Just better context.

That's the gap this kind of engineering closes.

Built by: Dereje Getie ,  Eyoel Nebiyu , Chalie Lijalem  , Liul Teshome Nuhamin Alemayehu and Rafia Kedir
github.com/Deregit2025/data-agent-forge

#DataEngineering #AIAgents #ContextEngineering #LLM #BuildingInPublicLinkedInLinkedIn Login, Sign in | LinkedInLogin to LinkedIn to keep in touch with people you know, share ideas, and build your career.

---

Rafia  [10:09 AM]
our final article from medium

https://medium.com/p/4a1869e8dff9?postPublishedType=initialMediumBuilding Oracle Forge: What It Actually Takes to Make an AI Agent Work on Real Enterprise DataTeam Gemini — Oracle Forge, Week 2 of 2Reading time5 min readToday at 10:03 AM

---

Nuhamin Alemayehu  [5:06 PM]
https://www.reddit.com/r/learnmachinelearning/s/61WFPyvypj
@channel
I have got two pass on music brainz dataset and wrote a reddit post about it. Since we are limited on API limits I will not porceed to the pancancer dataset until Dereje finishes running the whole dataset.

In the mean time I will update our signal branch. But I will write the final linkedin, twitter and reddit post once we finish and @Dereje Derib shares us the log file. (edited) RedditFrom the learnmachinelearning community on RedditExplore this post and more from the learnmachinelearning communityhttps://www.reddit.com/r/learnmachinelearning/s/61WFPyvypj

