from vermithor.audio.speech import SpeechRecognizer


class VoiceListener:

    def __init__(self):

        self.recognizer = SpeechRecognizer()
        self.running = True

    def preload(self):

        return self.recognizer.initialize()

    def listen(self):

        if not self.running:
            return ""

        return self.recognizer.listen()

    def listen_wake(self):

        if not self.running:
            return ""

        return self.recognizer.listen_wake()

    def listen_command(self):

        if not self.running:
            return ""

        return self.recognizer.listen_command()

    def stop(self):

        self.running = False

        try:

            self.recognizer.close()

        except Exception:
            pass

    def close(self):

        self.stop()