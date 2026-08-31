import queue
import threading
import tkinter as tk
from tkinter import ttk

try:
    import pystray
    from PIL import Image, ImageDraw

    TRAY_AVAILABLE = True

except ImportError:
    pystray = None
    Image = None
    ImageDraw = None

    TRAY_AVAILABLE = False

from vermithor.gui.theme import (
    BACKGROUND,
    PANEL,
    TEXT,
    ACCENT,
    MUTED
)


class VermithorWindow:

    def __init__(self, assistant):

        self.assistant = assistant

        self.events = queue.Queue()

        self.root = tk.Tk()

        self.root.title(
            "Vermithor"
        )

        self.root.geometry(
            "1000x680"
        )

        self.root.minsize(
            820,
            560
        )

        self.root.configure(
            bg=BACKGROUND
        )

        # --------------------------------------------------------
        # WINDOW CLOSE
        # --------------------------------------------------------
        #
        # IMPORTANT:
        #
        # Closing the GUI does NOT shut down Vermithor.
        #
        # It only hides the interface.
        #
        # Vermithor's voice thread continues running.
        #
        self.root.protocol(
            "WM_DELETE_WINDOW",
            self._hide
        )

        # --------------------------------------------------------
        # TRAY
        # --------------------------------------------------------

        self.tray_icon = None
        self.tray_thread = None
        self.tray_running = False

        self._configure_style()

        self._build()

        self.assistant.set_event_callback(
            self._event
        )

        self.root.after(
            100,
            self._drain_events
        )

    # ============================================================
    # STYLE
    # ============================================================

    def _configure_style(self):

        style = ttk.Style()

        try:
            style.theme_use(
                "clam"
            )

        except Exception:
            pass

        style.configure(
            "Vermithor.TButton",
            font=(
                "Segoe UI",
                10,
                "bold"
            ),
            padding=(
                14,
                9
            )
        )

    # ============================================================
    # UI
    # ============================================================

    def _build(self):

        header = tk.Frame(
            self.root,
            bg=BACKGROUND
        )

        header.pack(
            fill="x",
            padx=30,
            pady=(
                28,
                10
            )
        )

        tk.Label(
            header,
            text="VERMITHOR",
            font=(
                "Segoe UI",
                30,
                "bold"
            ),
            fg=ACCENT,
            bg=BACKGROUND
        ).pack(
            anchor="w"
        )

        tk.Label(
            header,
            text="ALWAYS-ON LOCAL DESKTOP ASSISTANT",
            font=(
                "Segoe UI",
                10
            ),
            fg=MUTED,
            bg=BACKGROUND
        ).pack(
            anchor="w",
            pady=(
                3,
                0
            )
        )

        # --------------------------------------------------------
        # STATUS
        # --------------------------------------------------------

        status_frame = tk.Frame(
            self.root,
            bg=PANEL
        )

        status_frame.pack(
            fill="x",
            padx=30,
            pady=(
                12,
                10
            )
        )

        self.dot = tk.Label(
            status_frame,
            text="●",
            font=(
                "Segoe UI",
                18
            ),
            fg=ACCENT,
            bg=PANEL
        )

        self.dot.pack(
            side="left",
            padx=(
                16,
                9
            ),
            pady=14
        )

        self.status = tk.Label(
            status_frame,
            text="Starting...",
            font=(
                "Segoe UI",
                12,
                "bold"
            ),
            fg=TEXT,
            bg=PANEL
        )

        self.status.pack(
            side="left"
        )

        # --------------------------------------------------------
        # LOG
        # --------------------------------------------------------

        log_frame = tk.Frame(
            self.root,
            bg=BACKGROUND
        )

        log_frame.pack(
            fill="both",
            expand=True,
            padx=30
        )

        self.log = tk.Text(
            log_frame,
            bg="#090d13",
            fg=TEXT,
            insertbackground=TEXT,
            selectbackground="#183b28",
            font=(
                "Consolas",
                11
            ),
            relief="flat",
            wrap="word",
            padx=16,
            pady=14
        )

        self.log.pack(
            fill="both",
            expand=True
        )

        self.log.configure(
            state="disabled"
        )

        # --------------------------------------------------------
        # INPUT
        # --------------------------------------------------------

        bottom = tk.Frame(
            self.root,
            bg=BACKGROUND
        )

        bottom.pack(
            fill="x",
            padx=30,
            pady=(
                14,
                24
            )
        )

        self.entry = tk.Entry(
            bottom,
            bg=PANEL,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            font=(
                "Segoe UI",
                11
            )
        )

        self.entry.pack(
            side="left",
            fill="x",
            expand=True,
            ipady=11,
            padx=(
                0,
                8
            )
        )

        self.entry.bind(
            "<Return>",
            lambda event: self._send()
        )

        ttk.Button(
            bottom,
            text="SEND",
            style="Vermithor.TButton",
            command=self._send
        ).pack(
            side="left",
            padx=4
        )

        ttk.Button(
            bottom,
            text="WAKE",
            style="Vermithor.TButton",
            command=self.assistant.wake
        ).pack(
            side="left",
            padx=4
        )

        ttk.Button(
            bottom,
            text="SLEEP",
            style="Vermithor.TButton",
            command=self._sleep
        ).pack(
            side="left",
            padx=4
        )

        ttk.Button(
            bottom,
            text="EXIT",
            style="Vermithor.TButton",
            command=self._close
        ).pack(
            side="left",
            padx=4
        )

        # --------------------------------------------------------
        # INITIAL LOG
        # --------------------------------------------------------

        self._write(
            "Vermithor is starting..."
        )

        self._write(
            "Say: Hello Vermithor, open Chrome"
        )

        self._write(
            "Say: Vermithor open Google"
        )

        self._write(
            "Say: Vermithor play Believer on YouTube"
        )

        self._write(
            "Say: Vermithor search Python on Google"
        )

        self._write(
            "Say: Vermithor what time is it"
        )

        self._write(
            ""
        )

        self._write(
            "Background speech is ignored until the wake phrase is detected."
        )

        self._write(
            "Closing this window keeps Vermithor running in the background."
        )

        if TRAY_AVAILABLE:

            self._write(
                "Vermithor system tray is enabled."
            )

        else:

            self._write(
                "System tray unavailable. Install pystray and Pillow to enable it."
            )

    # ============================================================
    # SYSTEM TRAY
    # ============================================================

    def _create_tray_image(self):

        if not TRAY_AVAILABLE:
            return None

        try:

            image = Image.new(
                "RGBA",
                (
                    64,
                    64
                ),
                (9, 13, 19, 255)
            )

            draw = ImageDraw.Draw(
                image
            )

            # Simple Vermithor-style icon.
            draw.ellipse(
                (
                    8,
                    8,
                    56,
                    56
                ),
                fill=(0, 190, 120, 255)
            )

            draw.ellipse(
                (
                    18,
                    18,
                    46,
                    46
                ),
                fill=(9, 13, 19, 255)
            )

            draw.ellipse(
                (
                    26,
                    26,
                    38,
                    38
                ),
                fill=(0, 190, 120, 255)
            )

            return image

        except Exception:

            return None

    def _start_tray(self):

        if not TRAY_AVAILABLE:
            return

        if self.tray_thread and self.tray_thread.is_alive():
            return

        self.tray_running = True

        self.tray_thread = threading.Thread(
            target=self._tray_worker,
            name="VermithorTray",
            daemon=True
        )

        self.tray_thread.start()

    def _tray_worker(self):

        try:

            image = self._create_tray_image()

            if image is None:
                self.tray_running = False
                return

            menu = pystray.Menu(

                pystray.MenuItem(
                    "Show Vermithor",
                    self._tray_show
                ),

                pystray.MenuItem(
                    "Wake Vermithor",
                    self._tray_wake
                ),

                pystray.MenuItem(
                    "Sleep Vermithor",
                    self._tray_sleep
                ),

                pystray.Menu.SEPARATOR,

                pystray.MenuItem(
                    "Exit Vermithor",
                    self._tray_exit
                )
            )

            self.tray_icon = pystray.Icon(
                "Vermithor",
                image,
                "Vermithor",
                menu
            )

            self.tray_icon.run()

        except Exception as exc:

            self.tray_running = False

            try:

                self.events.put(
                    (
                        "log",
                        f"System tray disabled: {type(exc).__name__}: {exc}"
                    )
                )

            except Exception:
                pass

    # ============================================================
    # TRAY ACTIONS
    # ============================================================

    def _tray_show(
        self,
        icon=None,
        item=None
    ):

        try:

            self.root.after(
                0,
                self._show
            )

        except Exception:
            pass

    def _tray_wake(
        self,
        icon=None,
        item=None
    ):

        try:

            self.assistant.wake()

        except Exception:
            pass

        try:

            self.root.after(
                0,
                self._show
            )

        except Exception:
            pass

    def _tray_sleep(
        self,
        icon=None,
        item=None
    ):

        try:

            threading.Thread(
                target=self.assistant.execute,
                args=("stop listening",),
                daemon=True
            ).start()

        except Exception:
            pass

    def _tray_exit(
        self,
        icon=None,
        item=None
    ):

        try:

            self.root.after(
                0,
                self._close
            )

        except Exception:
            pass

    # ============================================================
    # EVENTS
    # ============================================================

    def _event(
        self,
        kind,
        value
    ):

        self.events.put(
            (
                kind,
                value
            )
        )

    def _drain_events(self):

        try:

            while True:

                kind, value = (
                    self.events.get_nowait()
                )

                if kind == "status":

                    self.status.config(
                        text=str(value)
                    )

                elif kind == "heard":

                    self._write(
                        f"You: {value}"
                    )

                elif kind == "command":

                    self._write(
                        f"Command: {value}"
                    )

                elif kind == "response":

                    self._write(
                        f"Vermithor: {value}"
                    )

                elif kind == "log":

                    self._write(
                        f"System: {value}"
                    )

        except queue.Empty:

            pass

        try:

            if self.root.winfo_exists():

                self.root.after(
                    100,
                    self._drain_events
                )

        except Exception:

            pass

    # ============================================================
    # LOG
    # ============================================================

    def _write(
        self,
        text
    ):

        try:

            self.log.configure(
                state="normal"
            )

            self.log.insert(
                "end",
                str(text).rstrip()
                + "\n"
            )

            self.log.see(
                "end"
            )

            self.log.configure(
                state="disabled"
            )

        except Exception:

            pass

    # ============================================================
    # TEXT COMMAND
    # ============================================================

    def _send(self):

        command = (
            self.entry.get()
            .strip()
        )

        if not command:
            return

        self.entry.delete(
            0,
            "end"
        )

        threading.Thread(
            target=self.assistant.execute,
            args=(command,),
            daemon=True
        ).start()

    # ============================================================
    # SLEEP
    # ============================================================

    def _sleep(self):

        threading.Thread(
            target=self.assistant.execute,
            args=("stop listening",),
            daemon=True
        ).start()

    # ============================================================
    # SHOW
    # ============================================================

    def _show(self):

        try:

            self.root.deiconify()

            self.root.lift()

            self.root.attributes(
                "-topmost",
                True
            )

            self.root.after(
                100,
                lambda: self.root.attributes(
                    "-topmost",
                    False
                )
            )

            self.root.focus_force()

        except Exception:
            pass

    # ============================================================
    # HIDE
    # ============================================================

    def _hide(self):

        try:

            # IMPORTANT:
            #
            # Do NOT call assistant.shutdown() here.
            #
            # The voice engine continues running.
            #
            self.root.withdraw()

        except Exception:
            pass

    # ============================================================
    # CLOSE / COMPLETE EXIT
    # ============================================================

    def _close(self):

        try:

            # Completely stop Vermithor.
            self.assistant.shutdown(
                speak=False
            )

        except Exception:
            pass

        # --------------------------------------------------------
        # Stop system tray.
        # --------------------------------------------------------

        try:

            self.tray_running = False

            if self.tray_icon is not None:

                self.tray_icon.stop()

                self.tray_icon = None

        except Exception:
            pass

        # --------------------------------------------------------
        # Destroy GUI.
        # --------------------------------------------------------

        try:

            self.root.quit()

        except Exception:
            pass

        try:

            self.root.destroy()

        except Exception:
            pass

    # ============================================================
    # RUN
    # ============================================================

    def run(self):

        # --------------------------------------------------------
        # Start the voice engine FIRST.
        #
        # The GUI and system tray must never control the lifetime
        # of the voice listener.
        # --------------------------------------------------------

        self.assistant.start_voice_background()

        # --------------------------------------------------------
        # Start the system tray AFTER the voice thread exists.
        #
        # Tray errors cannot stop the voice engine.
        # --------------------------------------------------------

        self._start_tray()

        # --------------------------------------------------------
        # Start Tkinter.
        # --------------------------------------------------------

        self.root.mainloop()