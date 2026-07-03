from assistant.brain import get_response

print("Assistant is online. Type 'exit' to quit")

while True:
    user_input = input("You: ")
    
    if user_input.lower() == "exit":
        print("Assistant: Goodbye!")
        break
    
    res = get_response(user_input)
    print("Assistant: ", res)
    