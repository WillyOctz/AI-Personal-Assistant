from assistant import brain, llm, personality

original_gemini_proposal = llm.get_gemini_command_proposal


def forced_gemini_failure(user_message, system_instruction=None):
    return {
        "ok": False,
        "provider": "gemini",
        "reply": "",
        "suggested_command": None,
        "error": "Forced Gemini failure for Groq command test.",
    }


proposal_instruction = (
    personality.get_llm_system_instruction()
    + "\n\n"
    + personality.get_llm_command_proposal_instruction()
)


try:
    llm.get_gemini_command_proposal = forced_gemini_failure

    groq_command_result = llm.get_llm_command_proposal(
        "Please remember that I prefer Python for my projects.",
        proposal_instruction,
    )
finally:
    llm.get_gemini_command_proposal = original_gemini_proposal


if not groq_command_result["ok"]:
    raise AssertionError(
        f"Groq fallback failed: {groq_command_result['error']}"
    )

if groq_command_result["provider"] != "groq":
    raise AssertionError(
        "Expected Groq for the forced Gemini failure test."
    )

suggested_command = groq_command_result["suggested_command"]

if not suggested_command:
    raise AssertionError(
        "Expected Groq to return a command proposal."
    )

if not suggested_command.lower().startswith("remember "):
    raise AssertionError(
        f"Expected a remember command, got: {suggested_command}"
    )

if not brain.is_safe_llm_command(suggested_command):
    raise AssertionError(
        f"Nebula rejected Groq's command: {suggested_command}"
    )

print("\nGroq command provider:", groq_command_result["provider"])
print("Groq command:", suggested_command)
print("Groq command safe:", True)