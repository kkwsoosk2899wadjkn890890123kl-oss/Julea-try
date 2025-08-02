# Voice Autotuner

This project is a Python-based application that provides pitch correction for audio files. It can correct vocals to the nearest semitone (chromatic scale) or to specific musical scales (e.g., C Major, A Minor). The strength of the correction is also adjustable.

The autotuner was built with the goal of providing a more "natural" sounding pitch correction, not a robotic effect, although strong, robotic correction is possible by setting the correction strength to its maximum.

## Features

- **File-based processing:** Corrects the pitch of existing `.wav` files.
- **Scale Correction:** Corrects audio to a specific musical scale (Major/Minor) or to the chromatic scale.
- **Adjustable Strength:** Control how much the pitch is corrected, from subtle to strong.
- **Command-Line and GUI Interfaces:** Run the tool from the command line for scripting or use the simple graphical interface.

## Prerequisites

- **Python 3.8+**
- **PortAudio:** This is a system-level dependency required by the `pyaudio` library.
  - On Debian/Ubuntu: `sudo apt-get install portaudio19-dev`
  - On Mac (using Homebrew): `brew install portaudio`
  - On Windows, you may need to find a pre-compiled PortAudio library or build it from source.

## Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. **Install the Python dependencies:**
   It is highly recommended to use a virtual environment.
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   pip install -r requirements.txt
   ```

## How to Run

There are two ways to use the autotuner:

### 1. GUI Mode (Recommended)

The graphical interface provides an easy way to select files and configure the autotuner settings.

To run the GUI, execute the following command:
```bash
python gui.py
```
This will open a window where you can:
- Browse for an input `.wav` file.
- Specify a location to save the output `.wav` file.
- Choose a musical scale from the dropdown menu.
- Adjust the correction strength using the slider.
- Click "Run Processing" to start the correction.

### 2. Command-Line Mode

For automation or batch processing, you can use the `autotuner.py` script directly.

**Usage:**
```bash
python autotuner.py --input <input_file.wav> --output <output_file.wav> [options]
```

**Arguments:**
- `--input`: Path to the input `.wav` file (default: `test.wav`).
- `--output`: Path to save the corrected `.wav` file (default: `output.wav`).
- `--scale`: The musical scale to correct to. Examples: `'C-major'`, `'G-minor'`, `'chromatic'` (default).
- `--strength`: The correction strength, from `0.0` (no correction) to `1.0` (full correction) (default: `1.0`).

**Example:**
```bash
python autotuner.py --input my_vocals.wav --output corrected_vocals.wav --scale "A-minor" --strength 0.8
```

## Important Note on Real-Time (Live) Mode

The initial goal of this project was to include a real-time autotuner that processes microphone input live. However, the current implementation is **file-based only**. The real-time functionality requires a different architectural approach for audio streaming with the current libraries and has not been completed. The groundwork is laid in the `AudioStream` class, but it is not functional.
