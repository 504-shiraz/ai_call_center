# AI Call Center

An AI appointment assistant that supports both a terminal conversation and a real-time voice conversation over LiveKit. The assistant checks appointment availability and creates confirmed bookings in a SQLAlchemy-backed database.

## Features

- Conversational appointment availability checks and booking
- Business-hour validation from 09:00 to 17:00 in 30-minute intervals
- SQLite by default, with database configuration through `DATABASE_URL`
- Local Faster-Whisper speech-to-text with Silero voice activity detection
- Ollama-compatible LLM for the LiveKit voice workflow
- Local OpenAI-compatible TTS service for voice responses
- Structured logging for appointment, LLM, and speech-processing operations

## Architecture

```text
Customer
	|
	+--> app/main.py --------------------> AppointmentAgent
	|                                         |
	|                                         +--> AppointmentService
	|                                               |
	|                                               +--> AppointmentRepository
	|                                                     |
	|                                                     +--> SQLAlchemy / SQLite
	|
	+--> LiveKit room --> app/livekit/agent.py
									 |
									 +--> FasterWhisperSTT
									 +--> Silero VAD
									 +--> Ollama-compatible LLM
									 +--> OpenAI-compatible TTS
									 +--> AppointmentAgent
```

### Project layout

| Path | Responsibility |
| --- | --- |
| `app/main.py` | Interactive terminal entry point |
| `app/livekit/agent.py` | LiveKit worker and real-time voice session |
| `app/agent/` | Conversation agent and appointment tools |
| `app/services/` | Appointment, LLM, and speech-to-text services |
| `app/repositories/` | Database access for appointments |
| `app/models/` | SQLAlchemy persistence models |
| `app/database/` | Engine, sessions, schema initialization, and reset utility |
| `app/core/config.py` | Environment-based application settings |
| `data/` | Local SQLite database files; ignored by Git |
| `logs/` | Local application logs; ignored by Git |

## Requirements

- Python 3.11 or newer
- Ollama running locally with the configured model pulled
- For voice mode: a LiveKit project, an OpenAI-compatible LLM endpoint, and an OpenAI-compatible TTS endpoint

## Installation

Create and activate a virtual environment, then install the dependencies:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Copy the example configuration and update values for your environment:

```powershell
Copy-Item .env.example .env
```

The default database is `data/appointments.db`, created automatically on startup. Do not commit `.env`, database files, logs, model files, or local audio recordings.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_NAME` | `AI Call Center` | Application name |
| `APP_ENV` | `development` | Runtime environment |
| `DATABASE_URL` | SQLite in `data/appointments.db` | SQLAlchemy database URL |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server for the service layer |
| `OLLAMA_MODEL` | `qwen2.5:1.5b` | LLM model name |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434/v1` | LiveKit LLM endpoint |
| `LIVEKIT_URL` | Project-specific | LiveKit WebSocket URL |
| `LIVEKIT_API_KEY` | unset | LiveKit API key |
| `LIVEKIT_API_SECRET` | unset | LiveKit API secret |
| `KOKORO_MODEL` | `kokoro` | TTS model |
| `KOKORO_VOICE` | `af_bella` | TTS voice |
| `EMAIL_ENABLED` | `false` | Enable SMTP confirmation emails |
| `SMTP_HOST` | unset | SMTP server hostname |
| `SMTP_PORT` | `587` | SMTP server port |
| `SMTP_USERNAME` | unset | SMTP login username |
| `SMTP_PASSWORD` | unset | SMTP login password |
| `SMTP_FROM_EMAIL` | unset | Sender email address |
| `SMTP_USE_TLS` | `true` | Use STARTTLS for SMTP |

Keep API keys and secrets only in `.env` or your deployment secret store.

To send confirmation emails, set `EMAIL_ENABLED=true` and configure the SMTP variables. The appointment is saved even if the provider is unavailable; the agent reports that the booking succeeded but email delivery failed.

## Run the terminal assistant

Make sure Ollama is running and the configured model is available, then run:

```powershell
ollama pull qwen2.5:1.5b
python -m app.main
```

Type `exit` or `quit` to end the conversation.

## Run the LiveKit voice agent

Start the local Ollama and TTS services, configure the LiveKit credentials in `.env`, then launch the worker:

```powershell
python -m app.livekit.agent dev
```

The worker initializes the database, Faster-Whisper, and Silero VAD before accepting LiveKit sessions. The default speech-to-text configuration uses the `base` Faster-Whisper model on CPU with `int8` compute.

## Database utilities

Initialize the database explicitly:

```powershell
python -c "from app.database.connection import init_db; init_db()"
```

Clear all appointments from the local database:

```powershell
python -m app.database.reset
```

The reset command is destructive and intended for local development only.

## Development notes

- Appointment dates use `YYYY-MM-DD` and times use `HH:MM`.
- The service layer is the source of truth for availability and booking results.
- The repository checks confirmed appointments before creating a new booking.
- Local databases, logs, secrets, model downloads, and generated audio are excluded from Git by `.gitignore`.
