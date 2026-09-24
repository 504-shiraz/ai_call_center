import asyncio
import time
import uuid
import sys
import re
import numpy as np

from faster_whisper import WhisperModel

from livekit import rtc
from livekit.agents import stt

from livekit.agents.stt import (
    SpeechData,
    SpeechEvent,
    SpeechEventType,
    STT,
    STTCapabilities,
)
from livekit.agents.utils import AudioBuffer
from livekit.agents.types import APIConnectOptions

if sys.stdout:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

if sys.stderr:
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    
class FasterWhisperSTT(STT):

    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
        language: str = "en",
        cpu_threads: int = 4,
    ) -> None:
        
        super().__init__(
            capabilities=STTCapabilities(
                streaming=False,
                interim_results=False,
                diarization=False,
                aligned_transcript=False,
                offline_recognize=True,
            )
        )

        self._model_size = model_size
        self._language = language
        
        print()
        print("=" * 60)
        print("[FasterWhisperSTT] Initializing ....")
        print("=" * 60)

        print(
            f"[FasterWhisperSTT] Loading Model : \n\n"
            f"Model: {model_size} | Device: {device} | Compute Type: {compute_type} | Language: {language} | CPU Threads: {cpu_threads}"  
        )

        self._model = WhisperModel(model_size, device=device, compute_type=compute_type, cpu_threads=cpu_threads)

        print("[FasterWhisperSTT] Model Loaded Successfully!!")
        print("=" * 60)

    # =========================================
    # Model Information
    # =========================================
    
    @property
    def model(self) -> str:
        return f"FasterWhisperSTT-{self._model_size}-{self._language}"

    @property
    def provider(self) -> str:
        return "local"


    # =========================================
    # Speech Recognition
    # =========================================
    
    async def _recognize_impl(
        self, buffer: AudioBuffer, *, language, conn_options: APIConnectOptions
    ) -> stt.SpeechEvent:
        
        started_at = time.perf_counter()

        # ------------------------------------------------
        # Convert LiveKit AudioFrame(s) -> NumPy
        # ------------------------------------------------
        audio = self._audio_buffer_to_numpy(buffer)

        if audio.size == 0:
            print("[STT REJECT] Empty Audio Buffer")
            return self._empty_event()
        
        duration = len(audio) / 16000.0

        print(
            f"[FasterWhisperSTT] Processing "
            f"{len(audio)} Samples... "
            f"({duration:.2f}s audio) ..."
        )
        
        # ------------------------------------------------
        # Basic Audio Validation
        # ------------------------------------------------
        
        if duration < 0.20:
            print(f"[STT REJECT] Audio too Short:  {duration:.2f}s" )
            return self._empty_event()
        
        if self._is_silence(audio):
            print("[STT REJECT] Audio appears to be Silence/Noise")
            return self._empty_event()
        
        # -----------------------------------------------------------------
        # Faster-Whisper is CPU-heavy, so don't block LiveKit's event Loop
        # -----------------------------------------------------------------
        
        whisper_started = time.perf_counter()
        
        segments, info = await asyncio.to_thread(self._transcribe, audio, language)
        
        whisper_time = time.perf_counter() - whisper_started
        
        segments = list(segments)
        
        # -------------------------------------
        # Build Transcript
        # -------------------------------------
        
        text = " ".join(
            segment.text.strip() for segment in segments if segment.text.strip()
        ).strip()
        
        total_time = time.perf_counter() - started_at

        print(f"[FasterWhisperSTT] Total STT Time : {total_time:.2f}s")
        print(f"[FasterWhisperSTT] Whisper Time : {whisper_time:.2f}s")
        print(f"[FasterWhisperSTT] Detected Language: {info.language}")
        print(f"[FasterWhisperSTT] Language Probability: {info.language_probability:.2f}")
        print(f"[FasterWhisperSTT] Transcription Result : {text!r}", flush=True)


        # ---------------------------------
        # Empty Transcript
        # ---------------------------------

        if not text:
            print("[FasterWhisperSTT] Empty Transaction")
            return self._empty_event()
        
        # ------------------------------
        # Segment Quality Metrics
        # ------------------------------
        
        avg_logprobs = []
        no_speech_probs = []
        compression_ratios = []
        
        for segment in segments:
            
            avg_logprob = getattr(segment, "avg_logprob", None)
            no_speech_prob = getattr(segment, "no_speech_prob", None)
            compression_ratio = getattr(segment, "compression_ratio", None)
            
            if avg_logprob is not None:
                avg_logprobs.append(float(avg_logprob))
                
            if no_speech_prob is not None:
                no_speech_probs.append(float(no_speech_prob))
                
            if compression_ratio is not None:
                compression_ratios.append(float(compression_ratio))
        
        avg_logprob = (sum(avg_logprobs) / len(avg_logprobs) if avg_logprobs else None)
        no_speech_prob = (max(no_speech_probs) if no_speech_probs else None)
        compression_ratio = (max(compression_ratios) if compression_ratios else None)
        
        print( f"[STT Quality] avg_logprob={avg_logprob} | no_speech_prob={no_speech_prob} | compression_ratio={compression_ratio}" )
        
        print( f"[FasterWhisperSTT] Transcript: {text!r}", flush=True)
        
        # ----------------------------------
        # Basic Quality Gate
        # ----------------------------------
        
        reject_reason = self._quality_rejection_reason(
            text=text,
            avg_logprob=avg_logprob,
            no_speech_prob=no_speech_prob,
            compression_ratio=compression_ratio,
        )
        
        if reject_reason:
            print(f"[FastWhisperSTT] Transcript Rejected By Quality Gate") 
            print(f"[STT REJECT] {reject_reason} | Transcript={text!r}", flush=True)
            return self._empty_event()
        
        # -----------------------------
        # ACCEPT
        # -----------------------------
        
        print(f"[STT ACCEPT] {text!r}", flush=True)
        
        # -----------------------------
        # Segment Timestamps
        # -----------------------------
        
        start_time = (segments[0].start if segments else 0.0)
        end_time = (segments[-1].end if segments else 0.0)
        
        # -----------------------------
        # Speech Data
        # -----------------------------
        
        speech_data = SpeechData(
            language=(info.language or self._language),
            text=text,
            
            start_time=start_time,
            end_time=end_time,
            
            confidence=(
                float(info.language_probability)
                if info.language_probability is not None
                else 0.0
            ),
        )

        return SpeechEvent(
            type = SpeechEventType.FINAL_TRANSCRIPT,
            request_id = str(uuid.uuid4()),
            alternatives = [speech_data],
            speech_start_time = time.time(),
            speech_end_time = time.time(),
        )

    # ===============================================
    # Faster Whisper
    # ===============================================
    
    def _transcribe(self, audio: np.ndarray, language: str):
        
        segments, info = self._model.transcribe(
            audio,
            language=( language if language else self._language),
            task="transcribe",
            
            best_of=3,
            beam_size=3,
            
            temperature=0.0,
            condition_on_previous_text=False,
            
            compression_ratio_threshold=2.4,
            log_prob_threshold=-1.0,
            no_speech_threshold=0.6,
            
            vad_filter=False,
            word_timestamps=False,
        )
        
        # IMPORTANT:
        # Faster-Whisper Segments is a Generator.
        # Consume it here Inside the Worker Thread. 
        
        segments = list(segments)
        
        return segments, info
    
    
    # =========================================
    # Audio Quality
    # =========================================
    
    @staticmethod
    def _is_silence(audio: np.ndarray) -> bool:
        if audio.size == 0:
            return True
        
        rms = float(np.sqrt(np.mean(np.square(audio))))
        peak = float(np.max(np.abs(audio)))
        
        print(f"[Audio Quality] RMS={rms:.6f} | Peak={peak:.6f}")
        
        # Very quiet audio is most likely silence, microphone noise or room noise
        if rms < 0.003 and peak < 0.015:
            return True
        
        return False
    
    # =======================================
    # STT Quality Gate
    # =======================================
    
    @staticmethod
    def _quality_rejection_reason(
        text: str,
        avg_logprob,
        no_speech_prob,
        compression_ratio,
    ):
        text = text.strip()

        if not text:
            return "EMPTY TRANSCRIPT"
        
        # Whisper Confidence Transcription
        if ( avg_logprob is not None and avg_logprob < -1.0):
            return (f"LOW_LOG_PROBABILITY ({avg_logprob:.3f})")
        
        # Whisper Believes this is Probably Silence 
        if( no_speech_prob is not None and no_speech_prob > 0.65):
            return (f"HIGH_NO_SPEECH_PROBABILITY ({no_speech_prob:.3f})")
        
        # Possible Hallucination/Repetition
        if( compression_ratio is not None and compression_ratio > 2.4):
            return (f"HIGH_COMPRESSION_RATIO ({compression_ratio:.3f})")
        
        # Repeated Characters
        if FasterWhisperSTT._has_repeated_pattern(text):
            return "REPEATED TEXT PATTERN"
        
        # Suspicious Transcript Length
        words = text.split()
        
        if len(words) > 80:
            return "UNUSUALLY_LONG_TRANSCRIPT",
        
        return None
    
    # ========================================
    # Repeatition Detection
    # ========================================
    @staticmethod
    def _has_repeated_pattern(text: str)-> bool:
        normalized = re.sub(r"\s+", " ", text.lower()).strip()
        
        if not normalized:
            return False
        
        words = normalized.split()
        
        if len(words) >= 4:
            for size in range(1, 4):
                if len(words) >= size * 3:
                    last = words[-size:]
                    previous = words[-size * 2: -size]
                    before_previous = words[-size * 3: -size * 2]
                    
                    if( last == previous and previous ==  before_previous):
                        return True
        
        if len(normalized) >= 12:
            for char in "abcdefghijklmnopqrstuvwxyz":
                if char * 8 in normalized:
                    return True
                
        return False
    
    # ======================================
    # Empty Event
    # ======================================
    
    @staticmethod
    def _empty_event():
        return SpeechEvent(
            type=SpeechEventType.FINAL_TRANSCRIPT,
            request_id=str(uuid.uuid4()),
            alternatives=[],
        )
    
    
    # ======================================
    # Audio Conversion
    # ======================================

    @staticmethod
    def _audio_buffer_to_numpy(buffer: AudioBuffer) -> np.ndarray:
        """
        Convert LiveKit AudioFrame[s] or list[AudioFrame]
        into mono float32 PCM expected by Faster-Whisper.
        """
        
        # Single AudioFrame
        if isinstance(buffer, rtc.AudioFrame):
            frames = [buffer]
        
        # Multiple AudioFrames
        else:
            frames = list(buffer)

        if not frames:
            return np.array([], dtype=np.float32)

        audio_chunks = []

        for frame in frames:
            
            print(
                "[Audio Debug]",
                f"Sample Rate={frame.sample_rate}",
                f"Channels={frame.num_channels}",
                f"Samples={frame.samples_per_channel}",
            )

            # LiveKit AudioFrame.data is an Int16 PCM buffer.
            samples = np.frombuffer(frame.data, dtype=np.int16)

            # Stereo -> Mono
            if frame.num_channels > 1:
                samples = (samples.reshape(-1, frame.num_channels).mean(axis=1))

            audio_chunks.append(samples)

        # Combine Frames
        audio = np.concatenate(audio_chunks)

        # int16 PCM to float32 PCM conversion
        audio = (
            audio.astype(np.float32) / 32768.0
        )  # Convert to float32 in range [-1.0, 1.0]

        return audio

    # ==============================
    # Close
    # ==============================
    
    async def aclose(self) -> None:
        # Faster-Whisper doesn't require an async close.
        pass
