import os
import sys
import time

import truststore
truststore.inject_into_ssl()

from dotenv import load_dotenv

from livekit import agents
from livekit.agents import (Agent, AgentServer, AgentSession, JobContext, RoomInputOptions, TurnHandlingOptions, cli)
from livekit.plugins import openai, silero
# from livekit.agents.stt import StreamAdapter

from app.services.faster_whisper_stt import FasterWhisperSTT
from app.database.connection import init_db
from app.agent.appointment_agent import AppointmentAgent

load_dotenv()

# ---------------------------------------------------------
# Windows Console Encoding
# ---------------------------------------------------------

if sys.stdout:
    sys.stdout.reconfigure(
        encoding="utf-8",
        errors="replace",
    )

if sys.stderr:
    sys.stderr.reconfigure(
        encoding="utf-8",
        errors="replace",
    )
    
# ---------------------------------------------------------
# LiveKit Agent Server
# ---------------------------------------------------------

server = AgentServer()

# ---------------------------------------------------------
# Prewarm
# --------------------------------------------------------

def prewarm(proc):
    """
        Preload Models once when the Worker Starts!!
    """
    
    print("=" * 60)
    print("[PREWARM] Loading AI components...")
    print("=" * 60)
    
    init_db()
    
    # ----------------------------------------------------
    # Silero VAD
    # ----------------------------------------------------
    
    print("[Agent] Loading Silero VAD ...")
    
    proc.userdata["vad"] = silero.VAD.load()
    
    print("[VAD] Silero VAD Loaded Successfully!!")

    # --------------------------------------------------------
    # Faster Whisper
    # --------------------------------------------------------

    print("[STT] Loading Faster-Whisper...")

    proc.userdata["stt"] = FasterWhisperSTT(
        model_size="base",
        device="cpu",
        compute_type="int8",
        language="en",
        cpu_threads=4,
    )
    
    print("[STT] Faster-Whisper Loaded Successfully!!")

    print("=" * 60)
    print("[PREWARM] All components ready")
    print("=" * 60)
    
server.setup_fnc = prewarm

# def create_llm():
#     provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    
#     print()
#     print("=" * 60)
#     print("[LLM] Creating LLM")
#     print(f"[LLM] Provider: {provider}")
#     print("=" * 60)
    
#     if provider == "gemini":
#         api_key = os.getenv("GEMINI_API_KEY")
#         model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
        
#         if not api_key:
#             raise RuntimeError("GEMINI_API_KEY is missing from .env" )

#         print("[LLM] Provider : Gemini")
#         print(f"[LLM] Model    : {model}")
#         print("[LLM] Endpoint : Gemini OpenAI-compatible API")

#         return openai.LLM(
#             model=model,
#             api_key=api_key.strip(),
#             base_url=("https://generativelanguage.googleapis.com/v1beta/openai"),
#         )
        
#     elif provider == "ollama":

#         model = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")

#         base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1")

#         print("[LLM] Provider : Ollama")
#         print(f"[LLM] Model    : {model}")
#         print(f"[LLM] Endpoint : {base_url}")

#         return openai.LLM.with_ollama(
#             model=model,
#             base_url=base_url,
#         )
#     else:
#         raise RuntimeError(f"Unsupported LLM_PROVIDER: {provider}")

# ---------------------------------------------------------
# LiveKit RTC Session
# ---------------------------------------------------------

@server.rtc_session(
    agent_name="ai-call-center-agent"
)
async def entrypoint(ctx: JobContext):
    
    print()
    print("=" * 60)
    print("[AGENT] Starting AI Call Center Agent...")
    print("=" * 60)
    
    # -----------------------------------------
    # Connect to LiveKit Room
    # -----------------------------------------
    
    await ctx.connect()
        
    print(f"[LiveKit] Connected to room: {ctx.room.name}")

    # -----------------------------------------------------
    # Get Preload Components
    # -----------------------------------------------------

    whisper_stt = ctx.proc.userdata["stt"]
    vad = ctx.proc.userdata["vad"]
    
    print("[STT] Faster-Whisper Initialized Successfully!!")
    print("[VAD] Silero VAD Ready!!")
    
    # -----------------------------------------------------
    # Agent Session
    # -----------------------------------------------------
    
    session = AgentSession(
        
        # Local STT
        stt=whisper_stt,
        
        # Local Silero VAD
        vad = vad,
        
        # llm = create_llm(),
        
        # OLLAMA + Qwen
        llm=openai.LLM.with_ollama(
            model=os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1"),
        ),
        
        tts=openai.TTS(
            model=os.getenv("KOKORO_MODEL","kokoro"),
            voice=os.getenv("KOKORO_VOICE", "af_bella"),
            api_key="not-needed",
            base_url="http://127.0.0.1:8880/v1",
            response_format="wav",
        ),
        
        # OpenAI TTS
        # tts=openai.TTS(model="gpt-4o-mini-tts", voice="alloy"),
        
        # -----------------------------------------
        # TURN HANDLING
        # -----------------------------------------
        
        # We intentionally disable aggressive preemptive
        # generation because our CPU Faster-Whisper STT is
        # non-streaming and relatively slow.
        
        # This prevents the LLM from starting a response
        # while and old/unfinished STT request is still being
        # processed.
        
        turn_handling = TurnHandlingOptions(
            # VAD is already responsible for speech detection
            
            # This avoids relying on the defualt audio
            # turn-detector model for this CPU-first setup.
            
            turn_detection="vad",
            endpointing={
                "mode" : "fixed",
                
                # Give Whisper enough time to finish the
                # current utterance before committing the turn.
                
                "min_delay" : 0.50,
                "max_delay" : 2.0,
                # "min_delay" : 0.7,
                # "max_delay" : 2.0,
            },
            
            preemptive_generation={
                "enabled" : False,
            },
        ),
    )
    
    # -----------------------------------------
    # Start Session
    # -----------------------------------------
    agent = AppointmentAgent()
    
    print("\n" + "=" * 50)
    print("[DEBUG] AGENT TOOLS")
    for tool in agent.tools:
        print(f"[DEBUG TOOL] {tool.id}")
    print("=" * 50)
    
    await session.start(
        room=ctx.room,
        agent=agent,
        
        room_input_options=RoomInputOptions(
            audio_enabled=True,
            text_enabled=True,
            
            # Whisper Expects 16kHz audio
            audio_sample_rate=16000,
            
            # Mono Audio
            audio_num_channels=1,
            
            # 50ms audio frames
            audio_frame_size_ms=50,
        ),
    )
    
    # session.output.set_audio_enabled(False)
    
    # -----------------------------------------------------
    # Initial Greeting
    # -----------------------------------------------------
    
    await session.generate_reply(
        instructions="""
            Greet the Customer Professionally and Introduce Yourself as an AI Customer Support Assistant. Do not Ask Multiple Questions. After introducing yourself, ask how you can help.
        """
    )
    
# ---------------------------------------------------------
# Start Worker
# ---------------------------------------------------------
if __name__ == "__main__":
    cli.run_app(server)