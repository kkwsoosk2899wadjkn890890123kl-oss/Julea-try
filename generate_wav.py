import wave
import struct
import math

# --- Settings ---
FILENAME = "test.wav"
SAMPLE_RATE = 44100  # Hz
DURATION = 2  # seconds
FREQUENCY = 440.0  # Hz (A4 note)
AMPLITUDE = 32767  # Max amplitude for 16-bit audio
N_FRAMES = int(DURATION * SAMPLE_RATE)
N_CHANNELS = 1
SAMPLE_WIDTH = 2  # 2 bytes for 16-bit audio

# --- Generate Sine Wave Data ---
wav_file = wave.open(FILENAME, 'w')
wav_file.setparams((N_CHANNELS, SAMPLE_WIDTH, SAMPLE_RATE, N_FRAMES, 'NONE', 'not compressed'))

for i in range(N_FRAMES):
    # Calculate the sample value
    value = int(AMPLITUDE * math.sin(2 * math.pi * FREQUENCY * i / SAMPLE_RATE))
    # Pack the value as a 16-bit signed integer
    data = struct.pack('<h', value)
    wav_file.writeframes(data)

wav_file.close()
print(f"Generated '{FILENAME}' successfully.")
