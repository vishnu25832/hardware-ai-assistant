
# Linux Hardware AI Assistant

A command-line AI assistant that answers questions about a Linux computer's hardware using real system information and Google Gemini function calling.

Instead of guessing hardware specifications, the assistant selects dedicated inspection functions, retrieves system information, normalizes the results, and uses the returned data to answer questions.

## Features

- CPU model, architecture, physical cores, and logical processors.
- RAM capacity, available memory, and usage percentage.
- Storage device information and classification.
- GPU information when exposed by the operating system.
- Optional BIOS memory-slot inspection.
- Conversational follow-up questions.
- Structured hardware information returned as JSON.
- Graceful handling of unavailable hardware information.
- WSL and virtualization awareness.
- Read-only, allow-listed system inspection commands.

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
│   ├── test_assistant.py
│   └── test_inspector.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Prerequisites

- Python 3.10 or later.
- Linux operating system or WSL2.
- pip.
- Google Gemini API key.
- Linux utilities such as `lscpu`, `lsblk`, and `lspci`.

Some inspection features depend on the availability of system utilities and hardware access permissions.

## Installation

Clone the repository:

```bash
git clone https://github.com/vishnu25832/hardware-ai-assistant.git
```

Navigate into the project:

```bash
cd hardware-ai-assistant
```

Create a virtual environment:

```bash
python3 -m venv venv
```

Activate it:

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Open the file:

```bash
nano .env
```

Add your Gemini API key and model:

```env
GEMINI_API_KEY=your_actual_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash
```

Obtain an API key through Google AI Studio:

https://aistudio.google.com/apikey

Keep your API key private. The `.env` file is excluded from Git through `.gitignore`.

## Running the Assistant

Start the interactive assistant:

```bash
python -m ai.assistant
```

Example questions:

- What processor does my laptop have?
- How much RAM is available?
- How many RAM slots are free?
- Tell me about my GPU.
- Is my storage an SSD or HDD?
- Is the memory reported by WSL my physical laptop RAM?

Type `exit` or `quit` to close the assistant.

## Hardware Inspection

Run the hardware inspection module independently:

```bash
python -m hardware.inspector
```

The module produces structured JSON containing available operating system and hardware information.

The inspection functions include:

- `get_os_info()`
- `get_cpu_info()`
- `get_memory_info()`
- `get_memory_slot_info()`
- `get_storage_info()`
- `get_gpu_info()`
- `get_hardware_report()`

## Tool-Calling Architecture

The assistant uses Gemini function calling to select dedicated hardware inspection functions.

1. The user submits a hardware-related question.
2. Gemini determines which inspection function is relevant.
3. The selected function retrieves system information.
4. The function normalizes the output into structured data.
5. Gemini uses the returned information to formulate an answer.
6. The conversational session supports follow-up questions.

The assistant exposes focused inspection functions instead of giving the language model unrestricted shell access.

## Security

- Only explicitly allow-listed commands can be executed.
- Commands are executed without shell interpretation.
- User input is never passed directly to the operating system shell.
- Command execution has a timeout.
- Inspection functions do not perform hardware modifications.
- Sensitive memory serial numbers are excluded from parsed output.
- API credentials are stored in `.env`, not committed to Git.

## Privacy

This project uses the Google Gemini API.

User questions and information returned by selected inspection functions are sent to Google Gemini to generate responses.

Only the functions selected for a request should collect their corresponding hardware information. The application does not intentionally collect the complete hardware report for every question.

Do not include passwords, API keys, or unrelated personal information in questions.

For deployments requiring local-only processing, a separate local language model integration would be needed.

## Limitations

- Hardware information depends on the operating system and available system utilities.
- Some commands may require elevated permissions.
- BIOS memory-slot information may be unavailable in virtualized environments.
- WSL may expose virtualized CPU, memory, storage, and graphics resources rather than physical hardware.
- Storage interface information may be unknown when the operating system does not expose it.
- GPU identification depends on the information provided by the system.
- Hardware upgrade compatibility cannot be guaranteed when manufacturer specifications are unavailable.

The assistant should explicitly report unavailable information rather than inventing specifications.

## Running Tests

Run the complete test suite:

```bash
pytest -v
```

The tests cover:

- Command allow-list enforcement.
- Invalid command and command-injection rejection.
- CPU information parsing.
- Memory information.
- Storage classification.
- GPU detection.
- Memory-slot parsing and unavailable hardware information.
- Operating system detection.
- Assistant responses and API error handling.

## Future Improvements

- Broader Linux distribution support.
- More hardware-specific inspection capabilities.
- Improved hardware upgrade compatibility analysis.
- Additional automated integration tests.
- Optional local language model support.
