from assistant.brain import truncate_llm_context_text


text = "A" * 200

print(truncate_llm_context_text(text, 20))
print(len(truncate_llm_context_text(text, 20)))