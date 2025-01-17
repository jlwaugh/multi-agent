from nearai.registry import registry
from typing import Optional
import json
import time

class AgentSelector:
    def select_agent(self, query):
        try:
            agents = registry.list(
                namespace="",
                category="agent",
                tags="",
                total=888,
                offset=0,
                show_all=True,
                show_latest_version=True,
                starred_by=""
            )

            agents_list = "\n".join([
                f"Agent {i+1}:\n"
                f"  Name: {agent.name}\n"
                f"  Namespace: {agent.namespace}\n"
                f"  Version: {agent.version}\n"
                f"  Description: {agent.description}\n"
                f"  Tags: {', '.join(agent.tags)}\n"
                f"  Last Updated: {agent.updated}\n"
                f"  Stars: {agent.num_stars}\n"
                f"  Details: {json.dumps(agent.details, indent=2)}"
                for i, agent in enumerate(agents)
            ])

            messages = [
                {"role": "user", "content": f"""
                Analyze the following list of agents and determine which is most relevant to the user query.

                User Query: {query}

                Agent List:
                {agents_list}

                Instructions:
                1. Carefully read through all agents
                2. Consider name, description, tags, recency, and stars
                3. Evaluate the details
                4. Identify the agent most suited to handle the query
                5. Provide your reasoning
                6. Output in this exact JSON format:
                {{
                    "selected_agent_name": "...",
                    "selected_agent_namespace": "...",
                    "relevance_score": 0-100,
                    "reasoning": "Brief explanation of why this agent is most suitable"
                }}
                """}
            ]

            try:
                response = env.completion(
                    messages=messages,
                    max_tokens=555
                )

                try:
                    result = json.loads(response)

                    selected_agent = next(
                        (agent for agent in agents
                         if agent.name == result['selected_agent_name'] 
                         and agent.namespace == result['selected_agent_namespace']),
                        None
                    )

                    if selected_agent:
                        return {
                            'agent': selected_agent,
                            'score': result.get('relevance_score', 0),
                            'reasoning': result.get('reasoning', '')
                        }
                except (json.JSONDecodeError, KeyError) as parse_error:
                    print(f"Error parsing LLM response: {parse_error}")
                    print("Raw response:", response)
                    return None

            except Exception as completion_error:
                print(f"Completion error: {completion_error}")
                return None

        except Exception as e:
            print(f"Error in agent selection: {str(e)}")
            return None

def run_agent(owner: str, agent_name: str, version: str, query: Optional[str] = None, model: Optional[str] = None, fork_thread: bool = False):
    model = model or "llama-v3p1-70b-instruct"

    thread_id = env.run_agent(
        owner=owner,
        agent_name=agent_name,
        version=version,
        model=model,
        query=query,
        fork_thread=fork_thread
    )

    return thread_id

def display_thread(thread_id=None, max_wait=888, inactivity_threshold=23):
    start_time = time.time()
    last_activity_time = start_time
    processed_messages = set()
    last_message_count = 0

    print("\n🕵️ Monitoring agent thread...")

    while time.time() - start_time < max_wait:
        messages = env.list_messages(thread_id)
        current_time = time.time()

        if len(messages) > last_message_count:
            new_messages = [msg for msg in messages if msg['content'] not in processed_messages]

            for msg in new_messages:
                role = msg['role'].upper()
                content = msg['content']

                if ("Debugging status_update" in content or
                    "status_update in incorrect format" in content or
                    len(content.strip()) < 5):
                    continue

                print(f"\n🔷 {role}")
                print("-" * 50)
                print(content)
                print("-" * 50)

                processed_messages.add(content)

            last_message_count = len(messages)
            last_activity_time = current_time

        # Check for inactivity only if we've received messages before
        if last_message_count > 0 and current_time - last_activity_time > inactivity_threshold:
            try:
                env.request_user_input()
                user_input = input("\nEnter your response (or 'quit' to return to main prompt): ")
                if user_input.lower() == 'quit':
                    return
                env.add_reply(user_input)
                last_activity_time = current_time
            except Exception as e:
                print(f"Error requesting user input: {e}")

        time.sleep(1)

    print("\n🏁 Agent run complete.")

def main():
    selector = AgentSelector()

    while True:
        query = input("\nWhat do you need an agent to do? (or 'quit' to exit): ").strip()
        if not query:
            continue
        if query.lower() == 'quit':
            break

        best_match = selector.select_agent(query)

        if best_match:
            agent = best_match['agent']
            print(f"\n🔹 Found agent: {agent.namespace}/{agent.name}")
            print(f"Version: {agent.version}")
            print(f"Score: {best_match.get('score', 'N/A')}")
            print(f"Description: {agent.description}")

            if agent.tags:
                print(f"Tags: {', '.join(agent.tags)}")

            print(f"Last Updated: {agent.updated}")
            print(f"Stars: {agent.num_stars}")

            print("\nDetails:")
            print(json.dumps(agent.details, indent=2))

            if 'reasoning' in best_match:
                print(f"\nReasoning: {best_match['reasoning']}")

            if input("\nWould you like to call this agent? (y/n): ").lower().startswith('y'):
                print("\nCalling agent...")
                thread_id = run_agent(
                    agent.namespace,
                    agent.name,
                    "latest",
                    query=query,
                    fork_thread=False
                )
                print(f"🤖 Agent started in thread: {thread_id}")

                display_thread(thread_id)

                print("\nReturned to main prompt.")

        else:
            print("\nNo suitable agents found. Please try a different query.")

if __name__ == "__main__":
    main()
