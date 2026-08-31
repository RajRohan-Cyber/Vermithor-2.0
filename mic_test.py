import speech_recognition as sr


MICROPHONE_INDEX = 1


recognizer = sr.Recognizer()


print()
print("================================")
print("       VERMITHOR MIC TEST")
print("================================")
print()


microphone = sr.Microphone(
    device_index=MICROPHONE_INDEX
)


with microphone as source:

    print(
        "Preparing microphone..."
    )

    recognizer.adjust_for_ambient_noise(
        source,
        duration=1
    )

    print()
    print(
        "Microphone ready."
    )

    print()
    print(
        "Speak now..."
    )

    audio = recognizer.listen(
        source,
        timeout=None,
        phrase_time_limit=10
    )


print()
print(
    "Audio captured!"
)

print(
    "Recognizing..."
)

print()


try:

    text = recognizer.recognize_google(
        audio,
        language="en-US"
    )

    print(
        "You said:"
    )

    print(
        text
    )

except sr.UnknownValueError:

    print(
        "I could not understand the speech."
    )

except sr.RequestError as error:

    print(
        "Speech recognition error:"
    )

    print(
        error
    )