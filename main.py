from vermithor.core.assistant import Vermithor
from vermithor.gui.window import VermithorWindow


def main():

    assistant = None

    try:

        assistant = Vermithor()

        window = VermithorWindow(
            assistant
        )

        window.run()

    except KeyboardInterrupt:

        if assistant:

            assistant.shutdown(
                speak=False
            )

    except Exception:

        if assistant:

            assistant.shutdown(
                speak=False
            )

        raise


if __name__ == "__main__":

    main()