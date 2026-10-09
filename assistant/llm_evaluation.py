import json
from pathlib import Path

from assistant import llm
from assistant import personality


PROJECT_ROOT = Path(__file__).resolve().parent.parent
EVALUATION_FILE = (
    PROJECT_ROOT / "datasets" / "llm_eval_cases.jsonl"
)

def load_llm_evaluation_cases():
    cases = []
    
    with open(EVALUATION_FILE, "r") as file:
        for line_number, line in enumerate(file, start=1):
            text = line.strip()
            
            if not text:
                continue
            
            case = json.loads(text)
            
            message = str(case.get("message") or "").strip()
            expected_command = case.get("expected_command")
            
            if not message:
                raise ValueError(
                    f"Evaluation case {line_number} has no message."
                )
                
            if not isinstance(expected_command, bool):
                raise ValueError(
                    f"Evaluation case {line_number} needs a boolean "
                    "expected_command value."
                )
                
            if expected_command:
                command_prefix = str(
                    case.get("command_prefix") or ""
                ).strip()
                
                if not command_prefix:
                    raise ValueError(
                        f"Evaluation case {line_number} needs "
                        "command_prefix."
                    )
                    
            cases.append(case)
            
    return cases

def evaluate_llm_command_proposals(limit=None):
    cases = load_llm_evaluation_cases()
    
    if limit is not None:
        cases = cases[:max(1, int(limit))]
        
    system_instruction = (
        personality.get_llm_system_instruction() + "\n\n" + personality.get_llm_command_proposal_instruction()
    )
    
    results = []
    
    for case in cases:
        message = case["message"]
        expected_command = case["expected_command"]
        expected_prefix = str(
            case.get("command_prefix") or ""
        ).lower()
        
        result = llm.get_llm_command_proposal(
            message,
            system_instruction,
        )
        
        suggested_command = (
            result.get("suggested_command") or ""
        ).strip()
        
        response_exists = bool(
            str(result.get("reply") or "").strip()
        )
        
        if not result["ok"]:
            passed = False
            reason = result["error"]
            
        elif not response_exists:
            passed = False
            reason = "LLM returned an empty reply."
            
        elif not expected_command and not suggested_command:
            passed = True
            reason = "Correctly gave no command proposal."

        elif not expected_command and suggested_command:
            passed = False
            reason = "Unexpected command proposal."

        elif expected_command and not suggested_command:
            passed = False
            reason = "Expected a command proposal."

        elif suggested_command.lower().startswith(expected_prefix):
            passed = True
            reason = "Command prefix matched."

        else:
            passed = False
            reason = (
                f"Expected prefix '{expected_prefix}', got "
                f"'{suggested_command}'."
            )
            
        results.append({
            "message": message,
            "passed": passed,
            "reason": reason,
            "provider": result.get("provider"),
            "reply": result.get("reply"),
            "suggested_command": (
                suggested_command or None
            ),
        })
        
    total = len(results)
    passed = sum(result["passed"] for result in results)
    
    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "results": results,
    }