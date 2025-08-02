import pyaudio
import time
import argparse
import wave
import numpy as np
import aubio
import librosa

# --- Audio Settings ---
CHUNK = 1024
# Librosa's pitch shift works best with a larger FFT window
N_FFT = 2048
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

class AudioStream:
    """Handles live audio input and output."""
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.stream = None

    def callback(self, in_data, frame_count, time_info, status):
        """Passes audio data from input to output."""
        # Future processing will happen here.
        out_data = in_data
        return (out_data, pyaudio.paContinue)

    def start(self):
        """Opens and starts the audio stream."""
        # Note: Live mode is not fully implemented with librosa yet
        self.stream = self.p.open(format=FORMAT,
                                  channels=CHANNELS,
                                  rate=RATE,
                                  input=True,
                                  output=True,
                                  frames_per_buffer=CHUNK,
                                  stream_callback=self.callback)
        self.stream.start_stream()
        print("Audio stream started. (Press Ctrl+C to stop)")

    def stop(self):
        """Closes the audio stream."""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.p.terminate()
        print("Audio stream stopped.")

# --- Scale Definitions ---
SCALES = {
    'chromatic': list(range(12)),
    'major': [0, 2, 4, 5, 7, 9, 11],
    'minor': [0, 2, 3, 5, 7, 8, 10],
}
NOTES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

def get_scale_notes(scale_name):
    """Parses a scale name (e.g., 'C-major') and returns its MIDI notes."""
    if scale_name == 'chromatic':
        return SCALES['chromatic']

    try:
        root_note_str, scale_type = scale_name.split('-')
        root_note = NOTES.index(root_note_str.upper())
        scale_pattern = SCALES[scale_type.lower()]
        # Create the full scale by adding the root note to the pattern
        return [(root_note + i) % 12 for i in scale_pattern]
    except (ValueError, KeyError):
        print(f"Warning: Invalid scale '{scale_name}'. Defaulting to chromatic.")
        return SCALES['chromatic']

def process_file(input_filename, output_filename, scale_name, strength):
    """
    Reads an audio file, corrects its pitch based on scale and strength,
    and saves it to a new file.
    """
    try:
        print(f"Loading '{input_filename}'...")
        y, sr = librosa.load(input_filename, sr=RATE, mono=True)

        # Get the allowed notes for the selected scale
        allowed_notes = get_scale_notes(scale_name)
        print(f"Correcting to scale: {scale_name} ({[NOTES[n] for n in allowed_notes]})")
        print(f"Correction strength: {strength}")

        pitch_o = aubio.pitch("default", N_FFT, CHUNK, sr)

        y_corrected = np.zeros_like(y)

        print("Detecting and correcting pitch...")
        for i in range(0, len(y) - CHUNK, CHUNK):
            samples = y[i : i + CHUNK]
            pitch = pitch_o(samples)[0]

            if pitch > 0 and pitch_o.get_confidence() > 0.7:
                midi_note = librosa.hz_to_midi(pitch)

                # --- Find the nearest note in the scale ---
                note_distances = [((midi_note % 12) - scale_note + 6) % 12 - 6 for scale_note in allowed_notes]
                min_dist_idx = np.argmin(np.abs(note_distances))
                semitone_error = note_distances[min_dist_idx]

                target_midi_note = midi_note - semitone_error

                # --- Apply correction strength ---
                semitones_to_shift = semitone_error * strength * -1 # Multiply by -1 to correct the error

                if abs(semitones_to_shift) > 0:
                    corrected_samples = librosa.effects.pitch_shift(
                        y=samples, sr=sr, n_steps=semitones_to_shift, n_fft=N_FFT
                    )
                    y_corrected[i : i + CHUNK] = corrected_samples
                else:
                    y_corrected[i : i + CHUNK] = samples
            else:
                y_corrected[i : i + CHUNK] = samples

        last_chunk_start = (len(y) // CHUNK) * CHUNK
        y_corrected[last_chunk_start:] = y[last_chunk_start:]

        print(f"Saving corrected audio to '{output_filename}'...")
        import soundfile as sf
        sf.write(output_filename, y_corrected, sr)
        print("Processing complete.")

    except FileNotFoundError:
        print(f"Error: Input file '{input_filename}' not found.")
    except Exception as e:
        print(f"An error occurred: {e}")


def main():
    parser = argparse.ArgumentParser(description="A file-based autotuner.")
    parser.add_argument('--input', default='test.wav', help="Input WAV file.")
    parser.add_argument('--output', default='output.wav', help="Output WAV file.")
    parser.add_argument('--scale', default='chromatic', help="Musical scale to correct to (e.g., 'C-major', 'A-minor', 'chromatic').")
    parser.add_argument('--strength', type=float, default=1.0, help="Correction strength (0.0 to 1.0). 1.0 is full correction.")

    args = parser.parse_args()

    print("Starting autotuner in file mode...")
    process_file(args.input, args.output, args.scale, args.strength)

if __name__ == '__main__':
    main()
