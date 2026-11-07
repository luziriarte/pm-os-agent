# Loop Spec: Cortex PM Chief-of-Staff Agent

> Module 2 · Loop Engineering, ★ Deliverable 2
>
> ✅ **What this validates:** the agent knows when to run and when to stop, by the end you'll have proven a one-page Loop Spec with a trigger, a definition of "done," and explicit stop conditions.
>
> Your one-page blueprint for how the work you handed to the agent (M1) actually *runs*.
> An agent is just a prompt that fires itself, this spec says when it fires, what "done" means, and what it needs to do the job. Living document; refine as the course progresses.

## 1. Trigger & loop type

**Chosen type:** _heartbeat · cron · hook · goal_

_Why this type? (e.g. a Monday-morning cron that assembles the weekly update, plus a hook on a new PRD to propose stories.)_

## 2. Goal / definition of done

_What outcome is this loop responsible for? For a goal loop, what validation says "done"? (e.g. a status update grounded in real activity, queued for review, nothing posted.)_

## 3. Stop conditions

| Condition | What it looks like | What happens |
|---|---|---|
| **Success** | _…_ | _…_ |
| **Stuck / give up** | _…_ | _escalate / log / halt_ |
| **Escalate to human** | _…_ | _HITL checkpoint (from agent-line-map)_ |

## 4. State

_What persists across iterations, and what's the scope? (e.g. per-project context and last week's update; no cross-project confidential leakage.)_

## 5. The five things a loop can lean on

_`state` is always-on. `connectors` only if you already have one wired (e.g. a Jira key or Google MCP), otherwise just note it as a plan. `skills`, `subagents`, `work tree` scale with autonomy; "not needed yet, because…" is a valid answer._

| Component | For Cortex |
|---|---|
| **Work tree** (isolated workspace per run, a git worktree) | _…_ |
| **Skills** (reusable capabilities) | _…_ |
| **Plugins / connectors** (tools & access, optional if you don't have one yet) | _…_ |
| **Subagents** (independent check when the loop can't grade itself) | _placeholder → M3 orchestration-map.md_ |
| **State tracking** | _…_ |

> Context plan (M4) and the hand-off to bounds & evals (M5) come in later modules, you'll add them to their own deliverables then, not here.

## Link to live loop

_[path to your agent in `00-build/`]_
