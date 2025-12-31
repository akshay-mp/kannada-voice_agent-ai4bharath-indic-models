import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import time

def record_audio(filename="sample_audio.wav", duration=5, fs=16000):
    print(f"Recording for {duration} seconds... Speak now!")
    
    # Record audio
    recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16')
    sd.wait()  # Wait until recording is finished
    
    print("Recording finished.")
    
    # Save as WAV file
    wav.write(filename, fs, recording)
    print(f"Saved to {filename}")

if __name__ == "__main__":
    # You can change the duration here or via args if needed, keeping it simple for now
    record_audio()
