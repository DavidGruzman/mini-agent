from mini_agent import agent_loop, state
from mini_agent.llm_client import LLMClient


def main():
    root = state.resolve_project_root()
    messages = state.load_history(root)
    try:
        client = LLMClient()
    except Exception as e:
        print(f"error: {e}")
        return

    try:
        messages = agent_loop.ensure_summary(root, client, messages)
    except KeyboardInterrupt:
        print("\ninterrupted")
    except Exception as e:
        print(f"error: {e}")

    print(f"mini-agent ready in {root}. Type your instruction (Ctrl-D to exit).")
    while True:
        try:
            user_input = input("> ")
        except EOFError:
            print()
            break
        if not user_input.strip():
            continue
        user_message = {"role": "user", "content": user_input}
        messages.append(user_message)
        state.append_history(root, user_message)
        try:
            messages = agent_loop.run_turn(root, client, messages)
        except KeyboardInterrupt:
            print("\ninterrupted")
        except Exception as e:
            print(f"error: {e}")


if __name__ == "__main__":
    main()
