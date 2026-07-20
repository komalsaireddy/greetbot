from groq import Groq
from config import GROQ_API_KEY, LLM_MODEL
from memory.memory import Memory


class LLM:

    def __init__(self):

        self.client = Groq(api_key=GROQ_API_KEY)

        self.memory = Memory()

        self.messages = [
            {
                "role": "system",
                "content":
                "You are GreetBot, a friendly desktop AI assistant. "
                "You have long-term memory. "
                "Use the user's stored information whenever helpful."
            }
        ]

    def ask(self, prompt):

        memory = self.memory.all()

        memory_text = "\n".join(
            f"{k}: {v}"
            for k, v in memory.items()
        )

        full_prompt = f"""
User Memory:

{memory_text}

User:

{prompt}
"""

        self.messages.append(
            {
                "role": "user",
                "content": full_prompt
            }
        )

        response = self.client.chat.completions.create(
            model=LLM_MODEL,
            messages=self.messages,
        )

        answer = response.choices[0].message.content

        self.messages.append(
            {
                "role": "assistant",
                "content": answer
            }
        )

        return answer
