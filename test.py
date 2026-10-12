from assistant import brain, llm, personality

original_proposal_function = brain.llm.get_llm_command_proposal
original_system_instruction = brain.build_llm_system_instruction
original_conversation_prompt = brain.build_llm_conversation_prompt


def forced_llm_outage(user_message, system_instruction=None):
    return {
        "ok": False,
        "provider": "none",
        "reply": "",
        "suggested_command": None,
        "error": "Forced total provider outage.",
    }
    
outage_analysis = {
    "intent": "unknown",
    "group": "unknown",
    "source": "rule",
}


try:
    brain.llm.get_llm_command_proposal = forced_llm_outage

    # Keep this test focused on the final response branch.
    brain.build_llm_system_instruction = lambda user_input: "Test instruction."
    brain.build_llm_conversation_prompt = lambda user_input: user_input

    user_facing_response = brain.get_llm_fallback_response(
        "Explain Python tuples.",
        outage_analysis,
    )
finally:
    brain.llm.get_llm_command_proposal = original_proposal_function
    brain.build_llm_system_instruction = original_system_instruction
    brain.build_llm_conversation_prompt = original_conversation_prompt


if not isinstance(user_facing_response, str):
    raise AssertionError("Nebula's outage response must be text.")

if not user_facing_response.strip():
    raise AssertionError("Nebula's outage response cannot be empty.")

if outage_analysis["source"] != "llm_unavailable":
    raise AssertionError(
        "Nebula must record the LLM outage as its response source."
    )

if "Reply yes to confirm" in user_facing_response:
    raise AssertionError(
        "Nebula must not offer command confirmation during an outage."
    )

print("\nUser-facing outage response:", user_facing_response)
print("Outage source:", outage_analysis["source"])