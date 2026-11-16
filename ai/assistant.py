
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

from hardware.inspector import get_hardware_report


# Load environment variables
load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is missing. Add it to your .env file."
    )


# Initialize Gemini client
client = genai.Client(
    api_key=API_KEY,
    http_options=types.HttpOptions(
        api_version="v1beta"
    )
)

MODEL = "gemini-2.5-flash"


SYSTEM_INSTRUCTION = """
You are a Linux Hardware Q&A Assistant.

Your job is to answer questions about the user's computer hardware.

RULES:

1. Use get_hardware_report whenever actual system hardware
   information is required.

2. Never invent hardware specifications.

3. Clearly state when information is unavailable.

4. Distinguish physical hardware from virtualized
   environments such as WSL2.

5. Explain technical information in simple language.

6. Never execute arbitrary shell commands.

7. Never claim hardware was inspected unless the tool
   actually returned the relevant information.

8. Maintain context across follow-up questions.

9. If the user asks an unrelated question, respond briefly
   and redirect them to hardware-related topics.

10. Explain limitations when the environment does not
    expose physical hardware information.
"""


# Create a chat session with automatic function calling
chat = client.chats.create(
    model=MODEL,
    config=types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        tools=[get_hardware_report],
        temperature=0.2,
    ),
)


def ask_assistant(question: str) -> str:
    """Send a question using the persistent Gemini chat session."""

    if not question.strip():
        return "Please enter a question."

    try:
        response = chat.send_message(question)

        return response.text or "The AI returned no text response."

    except Exception as error:
        return f"AI request failed: {error}"


def main():

    print("\n======================================")
    print("       LINUX HARDWARE AI ASSISTANT")
    print("======================================")

    print("Ask questions about your computer.")

    print("\nExamples:")
    print("- What processor does my system use?")
    print("- How much RAM is available?")
    print("- Show my storage devices.")
    print("- What graphics device is detected?")
    print("- Is my system running inside WSL2?")

    print("\nType 'exit' to quit.\n")

    while True:

        try:
            question = input("You: ").strip()

            if question.lower() in ("exit", "quit"):
                print("\nAssistant: Goodbye!")
                break

            answer = ask_assistant(question)

            print(f"\nAssistant: {answer}\n")

        except KeyboardInterrupt:
            print("\n\nAssistant: Goodbye!")
            break


if __name__ == "__main__":
    main()
