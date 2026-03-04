"""
Stage 6 — Dawn Compliance Agent
Reviews each converted section, patches violations, and scores compliance.
Max 2 passes per section. Score < 0.7 on pass 2 → escalate (ship as-is + flag).

Outputs: compliance_report.json + updated .liquid files in run/sections/
"""

import json

import llm
import skills
from config import COMPLIANCE_MAX_PASSES, COMPLIANCE_MIN_SCORE
from state import RunState


def _run_compliance_pass(
    section_id: str,
    liquid: str,
    pass_number: int,
    violations_from_prev: list | None,
    system_prompt: str,
) -> dict:
    """Run one compliance pass. Returns agent JSON output."""
    user_payload: dict = {
        "section_id": section_id,
        "pass_number": pass_number,
        "liquid_content": liquid,
    }
    if violations_from_prev:
        user_payload["previous_violations"] = violations_from_prev

    result = llm.call_json(
        system_prompt,
        json.dumps(user_payload, indent=2),
        max_tokens=4000,
    )
    # Normalise: LLM may wrap output in a list
    if isinstance(result, list):
        result = result[0] if result and isinstance(result[0], dict) else {}
    if not isinstance(result, dict):
        result = {}
    return result


def run(state: RunState) -> dict:
    """
    Run Dawn Compliance Agent on all sections in sections_draft.
    Returns compliance_report dict {section_id: report}.
    """
    sections_draft = state.read_sections_draft()
    system_prompt = skills.prompt_dawn_compliance()

    compliance_report: dict = {}
    escalated: list[str] = []
    total_errors = 0

    for section_id, liquid in sections_draft.items():
        print(f"  → Compliance: {section_id}")
        current_liquid = liquid
        pass_report = None

        for pass_num in range(1, COMPLIANCE_MAX_PASSES + 1):
            prev_violations = None
            if pass_num == 2 and pass_report:
                prev_violations = pass_report.get("report", {}).get("violations_found", [])

            try:
                result = _run_compliance_pass(
                    section_id,
                    current_liquid,
                    pass_num,
                    prev_violations,
                    system_prompt,
                )
            except Exception as e:
                print(f"    ✗ Compliance pass {pass_num} failed for {section_id}: {e}")
                break

            patched = result.get("patched_content", "")
            report = result.get("report", {})
            score = report.get("compliance_score", 1.0)

            if patched:
                current_liquid = patched

            pass_report = result

            print(f"    pass {pass_num}: score={score:.2f}, "
                  f"violations={len(report.get('violations_found', []))}")

            if score >= COMPLIANCE_MIN_SCORE:
                break  # passed

            if pass_num == COMPLIANCE_MAX_PASSES:
                escalated.append(section_id)
                print(f"    ⚠ Escalated (score {score:.2f} < {COMPLIANCE_MIN_SCORE})")

        # Write final liquid (patched or original)
        state.write_section_liquid(section_id, current_liquid)

        # Store report
        report_data = pass_report.get("report", {}) if pass_report else {}
        compliance_report[section_id] = {
            "final_score": report_data.get("compliance_score", 1.0),
            "passes_run": pass_num,
            "escalated": section_id in escalated,
            "violations_found": report_data.get("violations_found", []),
            "unresolvable_flags": report_data.get("unresolvable_flags", []),
        }

        total_errors += sum(
            1 for v in report_data.get("violations_found", [])
            if v.get("severity") == "error" and not v.get("auto_fixed")
        )

    state.write_compliance_report(compliance_report)

    passed = len(sections_draft) - len(escalated)
    print(f"  ✓ Compliance done: {passed}/{len(sections_draft)} passed, "
          f"{len(escalated)} escalated, {total_errors} unresolved error(s)")
    return compliance_report
