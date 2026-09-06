from assistant.brain import get_response, get_startup_notification_message

print("Assistant is online. Type 'exit' to quit")

startup_message = get_startup_notification_message()

if startup_message:
    print("Assistant:", startup_message)

while True:
    user_input = input("You: ")
    
    if user_input.lower() == "exit":
        print("Assistant: Goodbye!")
        break
    
    res = get_response(user_input)
    print("Assistant: ", res)
    