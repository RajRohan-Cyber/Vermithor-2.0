import os
import shutil
import subprocess


class AppActions:

    ALIASES = {

        "notepad": "notepad.exe",

        "calculator": "calc.exe",

        "calc": "calc.exe",

        "paint": "mspaint.exe",

        "explorer": "explorer.exe",

        "file explorer": "explorer.exe",

        "cmd": "cmd.exe",

        "command prompt": "cmd.exe",

        "powershell": "powershell.exe",

        "terminal": "wt.exe",

        "chrome": "chrome.exe",

        "google chrome": "chrome.exe",

        "edge": "msedge.exe",

        "microsoft edge": "msedge.exe",

        "word": "winword.exe",

        "microsoft word": "winword.exe",

        "excel": "excel.exe",

        "microsoft excel": "excel.exe",

        "powerpoint": "powerpnt.exe",

        "discord": "discord.exe",

        "spotify": "spotify.exe",

        "steam": "steam.exe",

        "vlc": "vlc.exe",

        "code": "code.exe",

        "vscode": "code.exe",

        "vs code": "code.exe",

        "visual studio code": "code.exe"
    }

    def _start(
        self,
        executable,
        *args
    ):

        subprocess.Popen(

            [
                executable,
                *args
            ],

            shell=False,

            creationflags=getattr(
                subprocess,
                "CREATE_NO_WINDOW",
                0
            )
        )

    def open_app(
        self,
        name
    ):

        key = (
            name or ""
        ).lower().strip()

        executable = self.ALIASES.get(
            key,
            key
        )

        candidates = [
            executable
        ]

        # Chrome
        if key in {
            "chrome",
            "google chrome"
        }:

            candidates.extend([

                os.path.expandvars(
                    r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"
                ),

                os.path.expandvars(
                    r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
                ),

                os.path.expandvars(
                    r"%LocalAppData%\Google\Chrome\Application\chrome.exe"
                )
            ])

        # Edge
        elif key in {
            "edge",
            "microsoft edge"
        }:

            candidates.extend([

                os.path.expandvars(
                    r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
                ),

                os.path.expandvars(
                    r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
                )
            ])

        # VS Code
        elif key in {
            "code",
            "vscode",
            "vs code",
            "visual studio code"
        }:

            candidates.extend([

                os.path.expandvars(
                    r"%LocalAppData%\Programs\Microsoft VS Code\Code.exe"
                ),

                os.path.expandvars(
                    r"%ProgramFiles%\Microsoft VS Code\Code.exe"
                )
            ])

        for candidate in candidates:

            try:

                if os.path.isabs(
                    candidate
                ):

                    if not os.path.exists(
                        candidate
                    ):

                        continue

                elif not shutil.which(
                    candidate
                ):

                    continue

                self._start(
                    candidate
                )

                return (
                    f"{key.title()} is open."
                )

            except Exception:

                continue

        # Windows fallback
        try:

            subprocess.Popen(

                [
                    "cmd",
                    "/c",
                    "start",
                    "",
                    key
                ],

                shell=False,

                creationflags=getattr(
                    subprocess,
                    "CREATE_NO_WINDOW",
                    0
                )
            )

            return (
                f"I tried to open {key}."
            )

        except Exception as error:

            return (
                f"I couldn't open "
                f"{key}: {error}"
            )

    def close_app(
        self,
        name
    ):

        key = (
            name or ""
        ).lower().strip()

        executable = self.ALIASES.get(
            key,
            key
        )

        process = os.path.basename(
            executable
        )

        try:

            result = subprocess.run(

                [
                    "taskkill",
                    "/IM",
                    process,
                    "/F"
                ],

                capture_output=True,

                text=True,

                timeout=8,

                creationflags=getattr(
                    subprocess,
                    "CREATE_NO_WINDOW",
                    0
                )
            )

            if result.returncode == 0:

                return (
                    f"{key.title()} is closed."
                )

            return (
                f"{key.title()} was not running."
            )

        except Exception as error:

            return (
                f"I couldn't close "
                f"{key}: {error}"
            )

    def open_path(
        self,
        path
    ):

        try:

            path = os.path.abspath(
                os.path.expandvars(
                    os.path.expanduser(
                        path
                    )
                )
            )

            os.startfile(
                path
            )

            return (
                f"Opened {path}."
            )

        except Exception as error:

            return (
                f"I couldn't open "
                f"{path}: {error}"
            )