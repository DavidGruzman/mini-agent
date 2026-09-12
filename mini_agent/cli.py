from mini_agent import agent_loop, context_view, state, visualize
from mini_agent.llm_client import LLMClient


def main():
    root = state.resolve_project_root()
    messages = state.load_history(root)
    client = LLMClient()
    messages = agent_loop.ensure_summary(root, client, messages)

    print(f"mini-agent ready in {root}. Type your instruction (Ctrl-D to exit).")
    while True:
        try:
            user_input = input("> ").strip()
        except EOFError:
            print()
            break
        if not user_input:
            continue
        try:
            if user_input == "/visualize":
                print(f"wrote {visualize.generate_html(root)}")
            elif user_input == "/context":
                print(f"wrote {context_view.generate_html(root, messages)}")
            elif user_input == "/models":
                print("\n".join(client.list_models()))
            elif user_input == "/model" or user_input.startswith("/model "):
                arg = user_input[len("/model"):].strip()
                if arg:
                    client.model = arg
                print(f"model: {client.model}")
            else:
                messages.append({"role": "user", "content": user_input})
                state.append_history(root, messages[-1])
                messages = agent_loop.run_turn(root, client, messages)
        except KeyboardInterrupt:
            print("\ninterrupted")
        except Exception as e:
            print(f"error: {e}")


if __name__ == "__main__":
    main()
