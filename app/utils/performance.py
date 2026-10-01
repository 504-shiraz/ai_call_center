from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import time

@dataclass
class TurnMetrics:
    turn_id: int
    started_at: datetime = field(default_factory=datetime.now)
    
    audio_duration: Optional[float] = None
    
    stt_start: Optional[float] = None
    stt_end: Optional[float] = None
    
    llm_start: Optional[float] = None
    llm_end: Optional[float] = None
    
    tts_start: Optional[float] = None
    tts_end: Optional[float] = None
    
    transcript: Optional[str] = None
    response: Optional[str] = None
    
    @property
    def stt_latency(self):
        if self.stt_start is None or self.stt_end is None:
            return None
        
        return self.stt_end - self.stt_start
    
    @property
    def llm_latency(self):
        if self.llm_start is None or self.llm_end is None:
            return None
        
        return self.llm_end - self.llm_start
    
    @property
    def tts_latency(self):
        if self.tts_start is None or self.tts_end is None:
            return None
        
        return self.tts_end - self.tts_start
    
    @property
    def total_latency(self):
        starts = [
            value
            for value in [
                self.stt_start,
                self.llm_start,
                self.tts_start
            ]
            if value is not None
        ]
        
        ends = [
            value
            for value in [
                self.stt_end,
                self.llm_end,
                self.tts_end
            ]
            if value is not None
        ]
        
        if not starts or not ends:
            return None
        
        return max(ends) - min(starts)
    
class PerformanceTracker:

    def __init__(self):
        self.turn_counter = 0
        self.current_turn: Optional[TurnMetrics] = None
        self.history: list[TurnMetrics] = []

    def start_turn(self):
        self.turn_counter += 1

        self.current_turn = TurnMetrics(turn_id=self.turn_counter)

        print()
        print("=" * 70)
        print(f"[PERFORMANCE] TURN #{self.turn_counter}")
        print("=" * 70)

        return self.current_turn

    def finish_turn(self):
        if not self.current_turn:
            return

        self.history.append(self.current_turn)

        turn = self.current_turn

        print()
        print("-" * 70)
        print(f"[PERFORMANCE] TURN #{turn.turn_id}")
        print("-" * 70)

        if turn.audio_duration is not None:
            print(f"Audio Duration : {turn.audio_duration:.3f}s")

        if turn.stt_latency is not None:
            print(f"STT Latency    : {turn.stt_latency:.3f}s")

        if turn.llm_latency is not None:
            print(f"LLM Latency    : {turn.llm_latency:.3f}s")

        if turn.tts_latency is not None:
            print(f"TTS Latency    : {turn.tts_latency:.3f}s")

        if turn.total_latency is not None:
            print(f"Total Latency  : {turn.total_latency:.3f}s")

        print("-" * 70)

    def summary(self):
        if not self.history:
            return

        print()
        print("=" * 70)
        print("[PERFORMANCE] SESSION SUMMARY")
        print("=" * 70)

        stt_values = [
            t.stt_latency
            for t in self.history
            if t.stt_latency is not None
        ]

        llm_values = [
            t.llm_latency
            for t in self.history
            if t.llm_latency is not None
        ]

        tts_values = [
            t.tts_latency
            for t in self.history
            if t.tts_latency is not None
        ]

        total_values = [
            t.total_latency
            for t in self.history
            if t.total_latency is not None
        ]

        def avg(values):
            return sum(values) / len(values) if values else 0

        print(f"Turns          : {len(self.history)}")
        print(f"Avg STT        : {avg(stt_values):.3f}s")
        print(f"Avg LLM        : {avg(llm_values):.3f}s")
        print(f"Avg TTS        : {avg(tts_values):.3f}s")
        print(f"Avg Total      : {avg(total_values):.3f}s")

        print("=" * 70)