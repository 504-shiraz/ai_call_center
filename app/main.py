from app.agent.appointment_agent import AppointmentAgent

def main():
    
    agent = AppointmentAgent()
    
    print("=" * 50)
    print("Welcome to the AI Call Center!\n")
    print("Type 'exit' to end the Conversation.")
    print("=" * 50)
    
    while True:
        
        user_input = input("\nYou: ")
        
        if user_input.lower() in {"exit", "quit"}: 
            print("\n AI Call Center: Ending the Conversation. Goodbye!")
            break
        
        response = agent.respond(user_input)
        print(f"\nAI Call Center: {response}")
        
if __name__ == "__main__":
    main()