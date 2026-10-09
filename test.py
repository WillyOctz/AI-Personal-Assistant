from assistant.llm_evaluation import (
    evaluate_llm_command_proposals,
)


evaluation = evaluate_llm_command_proposals()

print({
    "total": evaluation["total"],
    "passed": evaluation["passed"],
    "failed": evaluation["failed"],
})

for result in evaluation["results"]:
    print("\nMessage:", result["message"])
    print("Passed:", result["passed"])
    print("Reason:", result["reason"])
    print("Provider:", result["provider"])
    print("Command:", result["suggested_command"])