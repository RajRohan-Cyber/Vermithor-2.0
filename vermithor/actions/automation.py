import time
from pathlib import Path

import pyautogui


class AutomationActions:

    def type_text(
        self,
        text
    ):

        try:

            pyautogui.write(
                text,
                interval=0.01
            )

            return "Text entered."

        except Exception as error:

            return (
                f"I couldn't type the text: "
                f"{error}"
            )


    def press(
        self,
        key
    ):

        try:

            pyautogui.press(
                key
            )

            return (
                f"Pressed {key}."
            )

        except Exception as error:

            return (
                f"I couldn't press {key}: "
                f"{error}"
            )


    def hotkey(
        self,
        *keys
    ):

        try:

            pyautogui.hotkey(
                *keys
            )

            return (
                "Keyboard shortcut executed."
            )

        except Exception as error:

            return (
                f"I couldn't execute the "
                f"shortcut: {error}"
            )


    def media(
        self,
        action
    ):

        keys = {

            "play": "playpause",

            "pause": "playpause",

            "next": "nexttrack",

            "previous": "prevtrack",

            "volume up": "volumeup",

            "volume down": "volumedown",

            "mute": "volumemute"

        }


        key = keys.get(
            action.lower().strip()
        )


        if not key:

            return (
                "I don't know that "
                "media command."
            )


        return self.press(
            key
        )


    def screenshot(self):

        try:

            folder = (
                Path.home()
                /
                "Pictures"
                /
                "Vermithor"
            )


            folder.mkdir(
                parents=True,
                exist_ok=True
            )


            path = (
                folder
                /
                f"screenshot_{int(time.time())}.png"
            )


            pyautogui.screenshot(
                str(path)
            )


            return (
                f"Screenshot saved to "
                f"{path}."
            )


        except Exception as error:

            return (
                f"I couldn't take a "
                f"screenshot: {error}"
            )