"""Independent validator (M3). A separate model call that never saw the drafting
context, so it can't inherit the draft's blind spots. Returns a pass/fail verdict.
The revision cap that stops a critic<->drafter loop lives in `agent.py`.
"""

from __future__ import annotations

import json

from prompts import CRITIC_SYSTEM

# The critic must answer in exactly this shape; the API enforces it.
VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["pass", "fail"]},
        "reasons": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["verdict", "reasons"],
    "additionalProperties": False,
}


def review(client, call_model, proposed_output: str, source_data: str) -> dict:
    """Return {"verdict": "pass"|"fail", "reasons": [...]} for a proposed output.

    `call_model` is agent.py's model call, so the critic shares the same model,
    effort and fallback settings, but none of the drafting conversation.
    """
    resp = call_model(
        client,
        system=CRITIC_SYSTEM,
        messages=[{"role": "user", "content":
                   f"SOURCE DATA Cortex used:\n{source_data}\n\n"
                   f"CORTEX PROPOSED OUTPUT:\n{proposed_output}"}],
        output_config={"format": {"type": "json_schema", "schema": VERDICT_SCHEMA}},
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    if resp.stop_reason == "refusal":
        verdict = {"verdict": "fail", "reasons": ["critic model declined to review"]}
    else:
        try:
            verdict = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            verdict = {"verdict": "fail", "reasons": ["critic returned unparseable output"]}
    verdict["_usage"] = resp.usage
    return verdict
