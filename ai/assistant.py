
import os

from dotenv import load_dotenv

from hardware.inspector import (
    get_cpu_info,
    get_gpu_info,
    get_memory_info,
    get_memory_slot_info,
    get_os_info,
    get_storage_info
)


load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


SYSTEM_INSTRUCTION = """
You are a Linux Hardware Q&A Assistant.

Your job is to answer questions about the user's computer hardware
using the available system-inspection tools.

Tool selection:
1. Select only the tool or tools needed to answer the user's question.
2. Do not collect the entire hardware report for a narrow question.
3. For CPU questions, use get_cpu_info.
4. For current RAM usage or installed memory, use get_memory_info.
5. For RAM slots, installed modules, or upgrade questions, use
   get_memory_slot_info.
6. For storage questions, use get_storage_info.
7. For graphics questions, use get_gpu_info.
8. For operating system questions, use get_os_info.
9. For upgrade questions, collect all relevant information before
   making a recommendation.

Accuracy:
1. Never invent hardware specifications.
2. Base hardware answers on tool results.
3. Clearly state when information is unavailable.
4. Never assume that a virtual device represents physical hardware.
5. Do not claim that a memory upgrade is compatible unless the
   available information supports that conclusion.
6. If maximum capacity, slot count, or compatibility is unavailable,
   explicitly say so.
7. Distinguish physical hardware from virtualized resources.
8. Explain WSL limitations when relevant.

Safety and privacy:
1. Never execute arbitrary shell commands.
2. Never request or suggest unrestricted shell execution.
3. Use only the provided inspection tools.
4. Do not ask the user to share passwords or API keys.
5. Do not expose hardware identifiers or private system information
   that is not needed to answer the question.

Conversation:
1. Maintain conversational context for follow-up questions.
2. Resolve follow-ups using the previous conversation when possible.
3. If information is insufficient, explicitly say so.
4. Explain technical information in clear, simple language.
"""


client = None
chat = None
initialization_error = None


def classify_api_error(error):
    """Convert Gemini API errors into understandable messages."""

    message = str(error).lower()

    if (
        "resource_exhausted" in message
        or "quota" in message
        or "429" in message
        or "rate limit" in message
    ):
        return (
            "Gemini API quota exceeded. "
            "Wait for the quota to reset or check your API usage."
        )

    if (
        "api_key_invalid" in message
        or "invalid api key" in message
        or "unauthenticated" in message
        or "401" in message
    ):
        return (
            "Gemini API authentication failed. "
            "Check your GEMINI_API_KEY in the .env file."
        )

    if (
        "permission_denied" in message
        or "permission denied" in message
        or "403" in message
    ):
        return (
            "Gemini API access denied. "
            "Check your API key permissions and model access."
        )

    if "timeout" in message or "timed out" in message:
        return (
            "The API request timed out. "
            "Check your network connection and try again."
        )

    if (
        "connection" in message
        or "network" in message
        or "dns" in message
        or "refused" in message
    ):
        return (
            "Unable to connect to Gemini. "
            "Check your network connection and try again."
        )

    if "not found" in message or "404" in message:
        return (
            "The requested Gemini model or resource was not found. "
            "Check the configured model name."
        )

    return (
        "Gemini API request failed. "
        "Check the API configuration and try again."
    )


def initialize_assistant():
    """Initialize the Gemini client and conversational session."""

    global client
    global chat
    global initialization_error

    client = None
    chat = None
    initialization_error = None

    if not API_KEY:
        initialization_error = (
            "GEMINI_API_KEY is missing from the .env file."
        )
        return

    try:
        from google import genai
        from google.genai import types

        inspection_tools = [
            get_cpu_info,
            get_memory_info,
            get_memory_slot_info,
            get_storage_info,
            get_gpu_info,
            get_os_info
        ]

        client = genai.Client(
            api_key=API_KEY,
            http_options=types.HttpOptions(
                api_version="v1beta"
            )
        )

        chat = client.chats.create(
            model=MODEL,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                tools=inspection_tools,
                temperature=0.2
            )
        )

    except Exception as error:
        initialization_error = classify_api_error(error)


def ask_assistant(question):
    """Send a question to Gemini and return its response."""

    if not question or not question.strip():
        return "Please enter a question."

    if not API_KEY:
        return (
            "Gemini API key is missing. "
            "Add GEMINI_API_KEY to your .env file."
        )

    if initialization_error:
        return initialization_error

    if chat is None:
        return "Gemini assistant is not initialized."

    try:
        response = chat.send_message(question)

        if response and response.text:
            return response.text

        return "The AI assistant returned an empty response."

    except Exception as error:
        return classify_api_error(error)


def main():
    print("\n======================================")
    print("       Linux Hardware AI Assistant")
    print("======================================")

    print("\nAI provider: Gemini")

    if initialization_error:
        print("\nInitialization error:")
        print(initialization_error)
        return

    print("\nAsk questions about your computer hardware.")

    print("\nExamples:")
    print("- What processor does my laptop have?")
    print("- How much RAM is available?")
    print("- How many RAM slots are free?")
    print("- Tell me about my GPU.")
    print("- Is my storage an SSD or HDD?")

    print("\nType 'exit' or 'quit' to close the assistant.\n")

    try:
        while True:
            question = input("You: ").strip()

            if question.lower() in ("exit", "quit"):
                print("Assistant: Goodbye!")
                break

            if not question:
                continue

            answer = ask_assistant(question)
            print(f"\nAssistant: {answer}\n")

    except KeyboardInterrupt:
        print("\nAssistant: Session interrupted. Goodbye!")


initialize_assistant()


if __name__ == "__main__":
    main()
