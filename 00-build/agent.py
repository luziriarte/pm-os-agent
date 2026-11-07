"""Cortex, a minimal, explicit agent loop you (and your coding agent) can read end
to end. This is the agent you ship: your PM chief-of-staff. You build it by
directing your coding agent (Claude Code / Cursor / Codex) to shape this file. You
never have to hand-write it.

Every bound the course talks about is visible right here in code, not buried in a
framework: the max-iteration counter, the cost cap, the revision cap, the
stop/escalate conditions, the auto-queue cap, and the absence of any publish tool.

Usage (ask your coding agent to run these for you, or run them yourself):
    python agent.py                # runs the happy-path task (weekly status update)
    python agent.py missing-data   # the stuck/escalate case
    python agent.py jailbreak       # the prompt-injection refusal case

Every run ends by showing the drafted status update in a FINAL STATUS UPDATE block
(or LAST DRAFT, held, if a bound trips), and saves it to run-output/. That file is
always a draft held for a human, it is never posted, there is no publish tool.

Requires ANTHROPIC_API_KEY in your environment (see .env.example). Model and bounds
are read from env so you can tune them, that tuning is your M5 deliverable.

The loop is deliberately transparent (hand-written tool-calling on the Anthropic
client) so a grader can see the machinery. Keep the bounds explicit if you rework it.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import anthropic

import tools
from critic import review
from prompts import CORTEX_SYSTEM

try:  # load .env if python-dotenv is installed; harmless if it isn't
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# --- Bounds (your M5 deliverable: tune these and justify them) ----------------
MODEL = os.environ.get("CORTEX_MODEL", "claude-opus-5-5")
# How hard Claude thinks before answering: low | medium | high | xhigh | max.
EFFORT = os.environ.get("CORTEX_EFFORT", "medium")
MAX_TOKENS = 16000  # per-response ceiling, so one reply can't run away
MAX_ITERATIONS = int(os.environ.get("CORTEX_MAX_ITERATIONS", "8"))
MAX_REVISIONS = int(os.environ.get("CORTEX_MAX_REVISIONS", "2"))
COST_CAP_USD = float(os.environ.get("CORTEX_COST_CAP_USD", "0.50"))
MAX_QUEUE_ITEMS = int(os.environ.get("CORTEX_MAX_QUEUE_ITEMS", "10"))
# Rough $ per 1M tokens for your chosen model, set to match its pricing.
PRICE_IN = float(os.environ.get("CORTEX_PRICE_IN_PER_M", "4.00"))
PRICE_OUT = float(os.environ.get("CORTEX_PRICE_OUT_PER_M", "20.00"))
# Re-sent context is cached: reading it back is much cheaper, writing it costs 1.25x.
PRICE_CACHE_READ = float(os.environ.get("CORTEX_PRICE_CACHE_READ_PER_M", "0.20"))
PRICE_CACHE_WRITE = PRICE_IN * 1.25

# If Claude's safety filter declines a request, retry it on Anthropic's
# recommended backup model inside the same call instead of failing the run.
FALLBACK_BETA = "server-side-fallback-2026-07-01"

TOOL_SCHEMAS = [
    {"name": "get_project",
     "description": "Look up a project by its ID (status, flags, linked PRD).",
     "input_schema": {"type": "object", "properties": {
         "project_id": {"type": "string"}}, "required": ["project_id"]}},
    {"name": "get_activity",
     "description": "Pull recent engineering activity for a project (merged PRs, open issues, Sev-1s).",
     "input_schema": {"type": "object", "properties": {
         "project_id": {"type": "string"}}, "required": ["project_id"]}},
    {"name": "search_past_updates",
     "description": "Search previous status updates and decisions for tone and precedent.",
     "input_schema": {"type": "object", "properties": {
         "query": {"type": "string"}}, "required": []}},
    {"name": "get_roadmap",
     "description": "Return the roadmap. Some items are flagged confidential/embargoed.",
     "input_schema": {"type": "object", "properties": {
         "query": {"type": "string"}}, "required": []}},
    {"name": "get_norms",
     "description": "Return the team norms / PM playbook the agent must follow.",
     "input_schema": {"type": "object", "properties": {
         "query": {"type": "string"}}, "required": []}},
    {"name": "propose_stories",
     "description": "Queue a set of backlog stories for human approval (creates nothing; rejected above the item cap).",
     "input_schema": {"type": "object", "properties": {
         "project_id": {"type": "string"},
         "stories": {"type": "array", "items": {"type": "string"}},
         "reason": {"type": "string"}}, "required": ["project_id", "stories"]}},
]


class Bounds:
    """Tracks spend and trips the cost cap. This is enforced OUTSIDE the model."""

    def __init__(self):
        self.cost = 0.0

    def add(self, usage) -> None:
        self.cost += usage_cost(usage)

    def over_cap(self) -> bool:
        return self.cost >= COST_CAP_USD


def usage_cost(usage) -> float:
    """Estimated $ for one model call, from the token counts the API reports."""
    return (usage.input_tokens * PRICE_IN
            + (usage.cache_creation_input_tokens or 0) * PRICE_CACHE_WRITE
            + (usage.cache_read_input_tokens or 0) * PRICE_CACHE_READ
            + usage.output_tokens * PRICE_OUT) / 1_000_000


def call_model(client, **kwargs):
    """One model call with the run-wide settings: effort, response cap, prompt
    caching of the re-sent context, and the refusal fallback."""
    return client.beta.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        output_config={"effort": EFFORT, **kwargs.pop("output_config", {})},
        cache_control={"type": "ephemeral"},
        betas=[FALLBACK_BETA],
        fallbacks="default",
        **kwargs,
    )


def response_text(resp) -> str:
    return "".join(b.text for b in resp.content if b.type == "text")


OUTPUT_DIR = Path(__file__).parent / "run-output"


def banner(text: str) -> None:
    print(f"\n{'=' * 64}\n{text}\n{'=' * 64}")


def emit_deliverable(which: str, draft: str, *, accepted: bool,
                     reason: str, cost: float) -> None:
    """Surface AND persist Cortex's drafted status update so it can't get lost in
    the scroll-back. This is still a DRAFT held for human review, never a post,
    there is no publish tool, and an escalated run is held on purpose.

    Runs on every exit: an accepted pass prints the FINAL update; a bound trip or
    escalation prints the LAST draft it managed to write plus why it was held.
    """
    banner("FINAL STATUS UPDATE (draft, validator-approved, NOT posted)" if accepted
           else "LAST DRAFT (held, NOT posted, escalated to a human)")
    if draft.strip():
        print(draft.rstrip())
    else:
        print("(Cortex stopped before it produced a draft, nothing to show.)")
    if not accepted:
        print(f"\nWhy it was held: {reason}")

    if draft.strip():
        OUTPUT_DIR.mkdir(exist_ok=True)
        out = OUTPUT_DIR / f"status-update-{which}.md"
        state = "accepted by validator" if accepted else "HELD, escalated"
        out.write_text(
            f"<!-- Cortex draft, {state}; NOT posted. Run cost ~ ${cost:.4f}. -->\n"
            f"<!-- {reason} -->\n\n{draft.rstrip()}\n", encoding="utf-8")
        print(f"\nSaved draft -> {out.relative_to(Path(__file__).parent)}  "
              f"(for your review, nothing was posted)")


def run(which: str = "happy") -> None:
    client = anthropic.Anthropic()
    bounds = Bounds()
    task = tools.get_task(which)
    if "error" in task:
        print(task)
        return

    banner(f"CORTEX RUN, fixture: task-{which}  (model {MODEL}, effort {EFFORT}, "
           f"auto-queue cap {MAX_QUEUE_ITEMS} items)")
    print(task["body"])

    messages = [
        {"role": "user", "content": f"PM task brief:\n\n{task['body']}"},
    ]
    source_log: list[str] = [task["body"]]
    revisions = 0
    last_draft = ""

    for step in range(1, MAX_ITERATIONS + 1):
        if bounds.over_cap():
            reason = f"cost cap ${COST_CAP_USD} hit at ${bounds.cost:.4f}"
            banner(f"BOUND TRIPPED, {reason}. Halting and escalating to a human.")
            emit_deliverable(which, last_draft, accepted=False,
                             reason=reason, cost=bounds.cost)
            return

        resp = call_model(client, system=CORTEX_SYSTEM, messages=messages,
                          tools=TOOL_SCHEMAS)
        bounds.add(resp.usage)
        # Keep Claude's whole reply (thinking + text + tool calls) in the history,
        # unchanged, so the next turn sees exactly what it said.
        messages.append({"role": "assistant", "content": resp.content})

        if resp.stop_reason in ("refusal", "max_tokens"):
            reason = ("the model declined this request (safety filter)"
                      if resp.stop_reason == "refusal"
                      else f"a single reply hit the {MAX_TOKENS}-token cap")
            banner(f"STOPPED, {reason}. Escalating to a human. "
                   f"Run cost ≈ ${bounds.cost:.4f}")
            emit_deliverable(which, last_draft, accepted=False,
                             reason=reason, cost=bounds.cost)
            return

        calls = [b for b in resp.content if b.type == "tool_use"]
        if calls:
            results = []
            for call in calls:
                fn, args = call.name, dict(call.input)
                result = tools.TOOLS[fn](**args)
                source_log.append(f"{fn}({args}) -> {json.dumps(result)}")
                print(f"\n[step {step}] TOOL {fn}({args})")
                print(f"          -> {json.dumps(result)[:300]}")
                results.append({"type": "tool_result", "tool_use_id": call.id,
                                "content": json.dumps(result)})
            # All results go back together in one message.
            messages.append({"role": "user", "content": results})
            continue

        # No tool calls => Cortex produced a proposed output. Validate it.
        proposed = response_text(resp)
        last_draft = proposed
        print(f"\n[step {step}] PROPOSED OUTPUT:\n{proposed}")

        banner("CRITIC, independent validation")
        verdict = review(client, call_model, proposed, "\n".join(source_log))
        # Count critic spend too.
        bounds.cost += usage_cost(verdict["_usage"])
        print(json.dumps({k: v for k, v in verdict.items() if k != "_usage"}, indent=2))

        if verdict["verdict"] == "pass":
            banner(f"HITL CHECKPOINT, status update + any proposed stories queued for "
                   f"your review. Nothing posted, no commitments made. "
                   f"Run cost ≈ ${bounds.cost:.4f}")
            emit_deliverable(which, proposed, accepted=True,
                             reason="validator passed", cost=bounds.cost)
            return

        if revisions >= MAX_REVISIONS:
            reason = f"validator rejected {MAX_REVISIONS}x (revision cap)"
            banner(f"REVISION CAP hit ({MAX_REVISIONS}). Escalating to a human "
                   f"instead of looping. Run cost ≈ ${bounds.cost:.4f}")
            emit_deliverable(which, last_draft, accepted=False,
                             reason=reason, cost=bounds.cost)
            return

        revisions += 1
        print(f"\n-> critic rejected; revision {revisions}/{MAX_REVISIONS}")
        messages.append({"role": "user", "content":
                         "A validator rejected that for these reasons: "
                         f"{verdict['reasons']}. Fix it or escalate."})

    banner(f"MAX ITERATIONS ({MAX_ITERATIONS}) reached without finishing. "
           f"Escalating. Run cost ≈ ${bounds.cost:.4f}")
    emit_deliverable(which, last_draft, accepted=False,
                     reason=f"max iterations ({MAX_ITERATIONS}) reached",
                     cost=bounds.cost)


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "happy")
