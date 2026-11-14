# Agent Line Map: Cortex PM Chief-of-Staff Agent

> Module 1 · The Agent Line
>
> ✅ **What this validates:** every risky action has a clear owner, by the end you'll have proven an above/below-the-line map with HITL checkpoints, scored on reversibility, blast radius, and measurability.

## The workflow, decision by decision

List every discrete decision or action in your agent's workflow, then score each one and place it **above** the line (a human owns it) or **below** (the agent owns it). Borderline calls get an HITL checkpoint.

| Decision / action | Reversibility (H/M/L) | Blast radius (H/M/L) | Measurability (H/M/L) | Above / Below | HITL? |
|---|---|---|---|---|---|
| Pull project state + activity | H | L | H | Below | None needed |
| Decide relevant context | H | M | M | HITL | PM reviews what was included or left out, and tunes the rules matrix |
| Draft the update | H | L | H | Below | None, since posting is gated separately |
| Decide tone/commitment level | M | H | L | HITL | PM approves the status colour and any date before it's final |
| Flag at-risk/escalation | H | M | M | Below | Flags are reviewed in the draft; no separate approval queue |
| Choose what to escalate | H | M | L | HITL | PM confirms each escalate-or-mention call, especially the ones not escalated |
| Propose a story batch (capped) | H | L | H | Below | Approval queue, capped at 10 stories |
| Post an update / approve a company-wide one | L | H | L | Above | Human only, always |

**Conditions on these scores:**
- *Decide relevant context* depends on a rules matrix the PM defines beforehand (e.g. anything financial or anything that stops the workflow always matters).
- *Decide tone/commitment level* would need a well-defined planner before a commitment could be measured as right or wrong.
- *Choose what to escalate* is scored as easy to reverse only while escalations notify just the PM, not the wider team.

## Agent anatomy (sketch)

- **Model:** Claude Opus 5.5 at medium effort by default (about $0.10 per run). For risky runs, such as a possible yellow/red status, an open critical bug or an escalation, raise effort to high. Not every call can be treated the same; some need more effort than others, so switching makes the agent more optimal, not only financially but also in results. _(Design only: today effort is set by hand in `.env`.)_
- **Tools:** five read-only tools: project lookup · engineering activity · past-update and decision search · roadmap · team norms. One queuing tool: propose stories, capped at 10 and only queued for approval. **No publish tool**, which enforces the "Above" verdict on posting in code.
- **Memory:** nothing carries over between runs; each run starts fresh. What persists is the source files Cortex reads every run (roadmap, team norms, past updates, decision log, projects), which the PM controls. Each run's draft is saved to `run-output/` for review.
- **Loop:** _placeholder, defined in M2 loop-spec.md_
- **Bounds:** _placeholder, defined in M5 bounds-and-evals.md_
- **Evals:** _placeholder, defined in M5 bounds-and-evals.md_

## The golden rule, applied

1. **Pull project state + activity** sits **below** the line because it's easy to reverse, has a low blast radius, and is easy to verify. Deciding factor: **reversibility**. If it's not right, it's easy to reject.
2. **Decide relevant context** is **HITL** because it's easy to reverse, has a medium blast radius, and is only moderately easy to verify. Deciding factor: **measurability**. Reviewing what Cortex picks early on is how I fine-tune the rules for what matters.
3. **Draft the update** sits **below** the line because it's easy to reverse, has a low blast radius, and is easy to verify. Deciding factor: **reversibility**. It's only a draft, easy to fix, review or discard.
4. **Decide tone/commitment level** is **HITL** because it's only moderately reversible, has a high blast radius, and is hard to verify. Deciding factor: **measurability**. Whether a date or colour is right depends on context like holidays or people out, so Cortex suggests and I push back on exceptions.
5. **Flag at-risk/escalation** sits **below** the line because it's easy to reverse, has a medium blast radius, and is moderately easy to verify. Deciding factor: **reversibility**. A false alarm is easy to dismiss, and an approval queue wouldn't catch missed flags anyway, so two lookouts beat one.
6. **Choose what to escalate** is **HITL** because it's easy to reverse while escalations only reach me, has a medium blast radius, and is hard to verify. Deciding factor: **measurability**. Reviewing the escalate-or-mention calls gives more chances to catch misses and improves measurability over time.
7. **Propose a story batch (capped)** sits **below** the line because it's easy to reverse, has a low blast radius, and is easy to verify. Deciding factor: **blast radius**. The stories haven't reached the team, so it's the right moment to edit or remove them.
8. **Post an update / approve a company-wide one** sits **above** the line because it's hard to reverse, has a high blast radius, and is hard to verify. Deciding factor: **reversibility**. Once posted it can't be undone, and a mistake could damage trust in my judgement and in the agent.

## Hardest call

**Choose what to escalate (#6).** I started by putting it above the line because an escalation could reach more people than just me and would be hard to undo. When I scored it, though, it turned out to be easy to reverse as long as escalations only notify me, so that wasn't the real reason. **Measurability settled it:** when something gets escalated, it's hard to tell whether it was the most important thing to escalate, or whether something else was left out. So Cortex's suggestions are useful, but the final decision should stay with us, so that we have the full picture. Verdict: **HITL**.
