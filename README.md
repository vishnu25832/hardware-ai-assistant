# Hardware AI Assistant

A command-line AI assistant that answers questions about a Linux computer's hardware using real system information and LLM tool calling.

Instead of guessing hardware specifications, the assistant retrieves information through a controlled inspection function and uses the results to answer questions.

## Features

- CPU model, architecture, physical cores, and logical processors.
- RAM capacity, available memory, and usage percentage.
- Storage device information.
- GPU information when exposed by the operating system.
- Optional BIOS memory-slot inspection.
- Conversational follow-up questions.
- Structured hardware information returned as JSON.
- Graceful handling of unavailable hardware information.

## Technology Stack

- Python
- Google Gemini API (`google-genai`)
- Python Dotenv
- psutil
- Linux system utilities
- pytest

## Project Structure

```text
hardware-ai-assistant/
├── ai/
│   ├── __init__.py
│   └── assistant.py
├── hardware/
│   ├── __init__.py
│   └── inspector.py
├── tests/
│   ├── __init__.py
│   └── test_inspector.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
