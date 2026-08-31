import pyaudio


audio = pyaudio.PyAudio()


print()
print("================================")
print("       VERMITHOR AUDIO DEVICES")
print("================================")
print()


for index in range(
    audio.get_device_count()
):

    device = audio.get_device_info_by_index(
        index
    )

    name = device.get(
        "name"
    )

    input_channels = device.get(
        "maxInputChannels"
    )

    sample_rate = device.get(
        "defaultSampleRate"
    )

    print(
        f"Index: {index}"
    )

    print(
        f"Name: {name}"
    )

    print(
        f"Input channels: {input_channels}"
    )

    print(
        f"Sample rate: {sample_rate}"
    )

    print(
        "-------------------------------"
    )


audio.terminate()