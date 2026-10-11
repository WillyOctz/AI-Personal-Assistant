from assistant.llm_evaluation import (
    evaluate_llm_command_proposals,
    format_llm_evaluation_report,
)
from assistant.brain import is_safe_llm_command

evaluation = evaluate_llm_command_proposals(
    command_validator=is_safe_llm_command
)

print(format_llm_evaluation_report(evaluation))