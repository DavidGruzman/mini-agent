from mini_agent import agent_loop, state, visualize
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
        if user_input.strip() == "/visualize":
            try:
                out = visualize.generate_html(root)
                print(f"wrote {out}")
            except Exception as e:
                print(f"error: {e}")
            continue
        if user_input.strip() == "/models":
            try:
                models = client.list_models()
                print("\n".join(models))
            except Exception as e:
                print(f"error: {e}")
            continue
        if user_input.strip() == "/model" or user_input.strip().startswith("/model "):
            arg = user_input.strip()[len("/model"):].strip()
            if not arg:
                print(f"current model: {client.model}")
            else:
                client.model = arg
                print(f"model set to: {client.model}")
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
