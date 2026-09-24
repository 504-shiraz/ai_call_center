from faster_whisper import WhisperModel

def main():
    print("Loading whisper Model...")
    
    model = WhisperModel("tiny", device="cpu", compute_type="int8")
    
    print("Model Loaded Successfully!!")
    
    audio_file = "test_audio_en.wav"
    
    print(f"Transcribing Audio File: {audio_file}")
    
    segments, info = model.transcribe(audio_file, language="en", beam_size=1)
    
    print(f"\nDetected Language: {info.language}")
    print(f"Language Probability: {info.language_probability}")
    
    print("\n-- Transcription Segments --")
    
    for segment in segments:
        print(f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}")
        
if __name__ == "__main__":
    main()