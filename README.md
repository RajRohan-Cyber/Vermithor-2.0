Vermithor 2.0

Vermithor 2.0 is a Python-based desktop voice assistant project.

This version was developed as an expansion of the earlier Vermithor 1.0 project. It combines voice input, speech recognition, text-to-speech, local AI, desktop automation, memory, and a graphical interface.

## Features

* Voice-controlled interaction
* Wake phrase detection
* Speech recognition using Faster-Whisper
* Text-to-speech responses
* Local AI integration through Ollama
* Application launching
* Browser-related actions
* File and system actions
* Basic automation
* Local memory
* Desktop GUI
* Windows startup support

## Technologies

* Python
* Faster-Whisper
* Ollama
* NumPy
* SciPy
* SoundDevice
* PyWin32
* PyAutoGUI
* yt-dlp
* Tkinter
* python-dotenv

## Project Structure

Vermithor-2.0/
├── app.py
├── main.py
├── mic_devices.py
├── mic_test.py
├── requirements.txt
├── start_vermithor.pyw
├── test_ai.py
├── Vermithor.spec
├── assets/
├── data/
└── vermithor/
    ├── __init__.py
    ├── actions/
    │   ├── __init__.py
    │   ├── apps.py
    │   ├── automation.py
    │   ├── browser.py
    │   ├── files.py
    │   ├── system.py
    │   └── web.py
    ├── audio/
    │   ├── __init__.py
    │   ├── listener.py
    │   ├── speech.py
    │   ├── tts.py
    │   └── wakeword.py
    ├── brain/
    │   ├── __init__.py
    │   └── ai.py
    ├── core/
    │   ├── __init__.py
    │   ├── assistant.py
    │   ├── logger.py
    │   ├── memory.py
    │   ├── router.py
    │   └── system.py
    └── gui/
        ├── __init__.py
        ├── theme.py
        └── window.py

## Requirements

Vermithor 2.0 is currently intended for Windows.

You will need:

* Python 3.13 or newer
* A working microphone
* Ollama
* A locally available Ollama model
* The Python packages listed in requirements.txt

## Installation

Clone or download the repository.

Install the Python dependencies:

pip install -r requirements.txt


Create a local .env file using .env.example as a reference.

Make sure Ollama is installed and running locally with the model specified in your configuration.

## Configuration

The project uses environment variables for configuration.

Copy:

.env.example

to:

.env

Then adjust the values if necessary.

The .env file is intentionally not included in the repository.

## Running Vermithor

The main application can be started with:

python main.py

You can also use:

python app.py

## Microphone Testing

The project includes microphone utilities for checking available audio devices and testing microphone input.

python mic_devices.py

and:

python mic_test.py

## AI Testing

The project also contains a small AI test script:

python test_ai.py

## Building

The project includes a PyInstaller specification file:

Vermithor.spec

Generated build files are not included in the source repository.

## Development

Vermithor 2.0 was built as a personal project to explore voice interfaces, speech recognition, local AI, desktop automation, and Python application development.

The project evolved from the earlier Vermithor 1.0 version and is still a work in progress.

## Project Status

Active personal project / development version.
