# Loop Spec: Cortex PM Chief-of-Staff Agent

> Module 2 · Loop Engineering, ★ Deliverable 2
>
> ✅ **What this validates:** the agent knows when to run and when to stop, by the end you'll have proven a one-page Loop Spec with a trigger, a definition of "done," and explicit stop conditions.
>
> Your one-page blueprint for how the work you handed to the agent (M1) actually *runs*.
> An agent is just a prompt that fires itself, this spec says when it fires, what "done" means, and what it needs to do the job. Living document; refine as the course progresses.

## 1. Trigger & loop type

**Chosen type:** cron + hook (cron primary, hook for ad-hoc requests).

**Why:** a weekly cron (Monday morning) assembles the regular leadership update, and a hook fires when someone sends Cortex an ad-hoc request. We need to account for both the weekly updates and the ad-hoc ones.

**Ruled out:**
- **Heartbeat:** updates are meant to be shared periodically. There's no reason to check every few minutes or hours, since updates become meaningful when there's more data from more activity.
- **Goal:** it doesn't help define how a run starts, more how it ends. (Goal-style checking still happens *inside* each run: draft → critic → revise.)

**Duplicate runs (idempotency):**
- **Weekly update:** one per project per week. If a draft already exists, a new trigger updates it instead of creating a second.
- **Ad-hoc requests:** deduped by message ID, so each request is handled exactly once.
- Neither is lost or duplicated, even when the cron and a request arrive at the same time.

## 2. Goal / definition of done

A run is **done** when the drafted status update (or the answer to an ad-hoc request), plus any requested stories, is written, **approved by the independent critic**, and queued for the PM's review. Cortex never sends or posts anything.

**Why:** it adds another level of review. It's not only getting the task done, but making sure it's approved by an independent agent.

**How it's detected:** the critic returns `"verdict": "pass"`, and the draft is saved to `run-output/`.

## 3. Stop conditions

| Condition | What it looks like | What happens |
|---|---|---|
| **Success** | Critic returns `pass`, and the draft and any stories are queued for approval. | Stop, save the draft, and **notify the PM only** that it's ready to review. _(Design: notification not built yet.)_ |
| **Stuck / give up** | Any of: the same data lookup fails **3** times · **8** steps used with no draft · critic rejects **2** times. | Stop, log why, and hold the last draft (if any) for the PM. No guessing, no further retries. |
| **Escalate to human** | Any of: a confidential/embargoed item would appear · a ship/GA date commitment is needed · the story batch exceeds the cap of 10 · a prompt-injection attempt · evidence points to a **yellow/red** status or an open **Sev-1**. | Stop and label the run `ESCALATE` with the reason and Cortex's suggested options. HITL checkpoints from the agent line map: tone/commitment (#4), choosing what to escalate (#6), posting (#8). |

**Why these stops:** we need to account for any possible error, and all three stuck signals are things that might get the system stuck. Escalation rules let us set specific rules, and also let the agent suggest possible options.

## 4. State

**Within a run:** everything Cortex pulled, its drafts, the critic's feedback, and its step, revision and cost counters. Cleared when the run ends.

**Across runs, kept per project (never shared between projects):**
- this week's draft for each project, so a new trigger updates it instead of duplicating it;
- the message IDs already handled;
- last week's update, for comparison.

**Why:** we need to make sure other projects' context doesn't confuse the agent. Keeping each project separate also means a confidential project can't leak into another project's update.

## 5. The five things a loop can lean on

_`state` is always-on. `connectors` only if you already have one wired (e.g. a Jira key or Google MCP), otherwise just note it as a plan. `skills`, `subagents`, `work tree` scale with autonomy; "not needed yet, because…" is a valid answer._

| Component | For Cortex |
|---|---|
| **Work tree** (isolated workspace per run, a git worktree) | Not needed yet, because Cortex doesn't edit files or code. It only reads data and saves drafts, and per-project state already keeps runs apart. |
| **Skills** (reusable capabilities) | Not needed yet, because Cortex does one workflow (status update + stories). Worth adding when it takes on more task types, e.g. "weekly update" and "story proposal" as separate skills. |
| **Plugins / connectors** (tools & access, optional if you don't have one yet) | **Planned, not wired:** today Cortex reads local practice files. Plan: read-only access to Jira/GitHub (activity), docs (roadmap, PRDs, norms) and past updates, plus one narrow write: a direct message **to the PM only** for the "ready to review" notification. No channel posting, no ticket creation. Why: it lets us set up the full workflow of reviewing context and also notifying us. |
| **Subagents** (independent check when the loop can't grade itself) | **Already in use:** the critic independently checks every draft and is part of the definition of done. Full design → M3 `orchestration-map.md`. |
| **State tracking** | Per-run working memory plus a per-project record across runs (see §4). |

> Context plan (M4) and the hand-off to bounds & evals (M5) come in later modules, you'll add them to their own deliverables then, not here.

## Link to live loop

- [`00-build/agent.py`](../00-build/agent.py): the loop and its stop conditions (success, stuck: 3 failed lookups · 8 steps · 2 critic rejections, escalate, and the stand-in PM notification).
- [`00-build/prompts.py`](../00-build/prompts.py): Cortex's instructions, including the escalation rules (yellow/red or Sev-1 → escalate with suggested options).
- Every run is logged to `00-build/run-output/run-log.md` (not committed).
