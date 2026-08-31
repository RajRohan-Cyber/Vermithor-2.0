import ctypes
import subprocess


class SystemActions:

    def lock(self):

        try:

            ctypes.windll.user32.LockWorkStation()

            return (
                "The computer has been locked."
            )

        except Exception as error:

            return (
                f"I couldn't lock the computer: "
                f"{error}"
            )


    def shutdown(self):

        try:

            subprocess.Popen(
                [
                    "shutdown",
                    "/s",
                    "/t",
                    "30"
                ],
                shell=False
            )

            return (
                "Shutdown scheduled for 30 seconds."
            )

        except Exception as error:

            return (
                f"I couldn't schedule shutdown: "
                f"{error}"
            )


    def restart(self):

        try:

            subprocess.Popen(
                [
                    "shutdown",
                    "/r",
                    "/t",
                    "30"
                ],
                shell=False
            )

            return (
                "Restart scheduled for 30 seconds."
            )

        except Exception as error:

            return (
                f"I couldn't schedule restart: "
                f"{error}"
            )


    def cancel_shutdown(self):

        try:

            subprocess.Popen(
                [
                    "shutdown",
                    "/a"
                ],
                shell=False
            )

            return (
                "Pending shutdown or restart cancelled."
            )

        except Exception as error:

            return (
                f"I couldn't cancel it: "
                f"{error}"
            )