import json
import os
import re
import time
import urllib.parse
import webbrowser


class BrowserActions:

    # ============================================================
    # BASIC URL
    # ============================================================

    def open_url(self, url):

        url = str(
            url or ""
        ).strip()

        if not url:
            return "I don't have a website to open."

        if not url.startswith(
            (
                "http://",
                "https://",
            )
        ):
            url = "https://" + url

        try:

            opened = webbrowser.open(
                url,
                new=2,
            )

            if opened:

                return (
                    f"Opened {url}."
                )

            return (
                f"I couldn't open {url}."
            )

        except Exception as exc:

            print(
                "Browser error:",
                type(exc).__name__,
                exc,
            )

            return (
                f"Could not open {url}."
            )

    # ============================================================
    # GOOGLE
    # ============================================================

    def open_google(self):

        return self.open_url(
            "https://www.google.com"
        )

    def search_google(
        self,
        query,
    ):

        query = str(
            query or ""
        ).strip()

        if not query:
            return (
                "What would you like me to search for?"
            )

        return self.open_url(
            "https://www.google.com/search?q="
            + urllib.parse.quote_plus(
                query
            )
        )

    # ============================================================
    # YOUTUBE
    # ============================================================

    def open_youtube(self):

        return self.open_url(
            "https://www.youtube.com"
        )

    def search_youtube(
        self,
        query,
    ):

        query = str(
            query or ""
        ).strip()

        if not query:
            return (
                "What should I search for on YouTube?"
            )

        return self.open_url(
            "https://www.youtube.com/results"
            "?search_query="
            + urllib.parse.quote_plus(
                query
            )
        )

    # ============================================================
    # CLEAN YOUTUBE QUERY
    # ============================================================

    @staticmethod
    def _clean_youtube_query(
        query,
    ):

        query = str(
            query or ""
        ).strip()

        if not query:
            return ""

        # Remove YouTube wording.

        query = re.sub(
            r"\b(?:on|in)\s+you\s*tube\b",
            "",
            query,
            flags=re.IGNORECASE,
        )

        # Remove command filler.

        query = re.sub(
            r"^(?:please\s+)+",
            "",
            query,
            flags=re.IGNORECASE,
        )

        query = re.sub(
            r"\s+(?:please|for me)\s*$",
            "",
            query,
            flags=re.IGNORECASE,
        )

        # Remove media words only when they are at
        # the end of the query.

        query = re.sub(
            r"\s+(?:song|music|track|video)\s*$",
            "",
            query,
            flags=re.IGNORECASE,
        )

        query = re.sub(
            r"\s+",
            " ",
            query,
        ).strip()

        return query

    # ============================================================
    # RESULT SCORING
    # ============================================================

    @staticmethod
    def _score_youtube_result(
        title,
        query,
    ):

        title = str(
            title or ""
        ).lower()

        query = str(
            query or ""
        ).lower()

        score = 0

        # --------------------------------------------------------
        # Exact query words
        # --------------------------------------------------------

        query_words = [
            word
            for word in re.findall(
                r"[a-z0-9]+",
                query,
            )
            if len(word) >= 2
        ]

        for word in query_words:

            if word in title:

                score += 12

        # --------------------------------------------------------
        # MUSIC RESULT INDICATORS
        # --------------------------------------------------------

        music_terms = (

            "official music video",

            "official video",

            "official audio",

            "official lyric video",

            "lyric video",

            "lyrics",

            "audio",

            "song",

            "music",

            "full song",

            "full video",

            "video song",

            "original song",

            "remix",

            "cover",

            "slowed",

            "reverb",

            "lofi",

        )

        for term in music_terms:

            if term in title:

                score += 8

        # --------------------------------------------------------
        # STRONG TITLE MATCH
        # --------------------------------------------------------

        compact_query = re.sub(
            r"[^a-z0-9]",
            "",
            query,
        )

        compact_title = re.sub(
            r"[^a-z0-9]",
            "",
            title,
        )

        if (
            compact_query
            and compact_query in compact_title
        ):

            score += 30

        # --------------------------------------------------------
        # BAD RESULTS
        # --------------------------------------------------------

        bad_terms = (

            "news",

            "breaking news",

            "live news",

            "headlines",

            "khabar",

            "samachar",

            "today news",

            "politics",

            "political",

            "debate",

            "report",

            "reaction",

            "review",

            "interview",

            "podcast",

            "shorts",

            "#shorts",

        )

        for term in bad_terms:

            if term in title:

                score -= 25

        # --------------------------------------------------------
        # LIVE
        # --------------------------------------------------------

        if re.search(
            r"\blive\b",
            title,
        ):

            score -= 20

        # --------------------------------------------------------
        # TRAILER
        # --------------------------------------------------------

        if "trailer" in title:

            score -= 20

        return score

    # ============================================================
    # FIND YOUTUBE VIDEO
    # ============================================================

    def _find_youtube_video(
        self,
        query,
    ):

        try:

            import requests

        except Exception as exc:

            print(
                "requests library is not available:",
                exc,
            )

            return None, None

        # ------------------------------------------------------------
        # NOTE:
        #
        # yt-dlp's search (ytsearch) goes through its "extractor"
        # layer, which YouTube has been actively blocking for
        # automated tools — even with the android client trick.
        #
        # Instead we fetch the exact same search-results page a
        # real browser loads (youtube.com/results?search_query=...)
        # and read the video data straight out of the page's
        # embedded "ytInitialData" JSON. This is the same request
        # your browser makes when you type into the YouTube search
        # box, so it is far less likely to be blocked.
        # ------------------------------------------------------------

        search_url = (
            "https://www.youtube.com/results?search_query="
            + urllib.parse.quote_plus(
                query
            )
        )

        headers = {

            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),

            "Accept-Language": "en-US,en;q=0.9",

        }

        try:

            response = requests.get(
                search_url,
                headers=headers,
                timeout=10,
            )

            response.raise_for_status()

        except Exception as exc:

            print(
                "YouTube search request failed:",
                type(exc).__name__,
                exc,
            )

            return None, None

        match = re.search(
            r"var ytInitialData\s*=\s*(\{.*?\});</script>",
            response.text,
        )

        if not match:

            match = re.search(
                r"ytInitialData\"\]\s*=\s*(\{.*?\});",
                response.text,
            )

        if not match:

            print(
                "Could not find YouTube search data "
                "in the page for:",
                query,
            )

            return None, None

        try:

            data = json.loads(
                match.group(1)
            )

        except Exception as exc:

            print(
                "Could not parse YouTube search data:",
                type(exc).__name__,
                exc,
            )

            return None, None

        # --------------------------------------------------------
        # WALK THE JSON TREE FOR VIDEO RESULTS
        #
        # YouTube's page JSON is deeply nested and changes shape
        # from time to time, so instead of hard-coding the exact
        # path we just walk the whole tree and collect every
        # "videoRenderer" block we find, in the order they appear
        # (which is YouTube's own relevance order).
        # --------------------------------------------------------

        entries = []

        def walk(node):

            if isinstance(node, dict):

                renderer = node.get(
                    "videoRenderer"
                )

                if isinstance(renderer, dict):

                    video_id = str(
                        renderer.get(
                            "videoId",
                            "",
                        )
                    ).strip()

                    title_runs = (
                        renderer
                        .get("title", {})
                        .get("runs", [])
                    )

                    title = (
                        title_runs[0].get("text", "")
                        if title_runs
                        else ""
                    ).strip()

                    if video_id and title:

                        entries.append(
                            (title, video_id)
                        )

                for value in node.values():

                    walk(value)

            elif isinstance(node, list):

                for item in node:

                    walk(item)

        walk(data)

        if not entries:

            print(
                "YouTube search returned "
                "zero entries for:",
                query,
            )

            return None, None

        ranked = []

        # Only the first ~15 results actually matter, and this
        # keeps scoring fast on longer pages.
        for title, video_id in entries[:15]:

            score = (
                self._score_youtube_result(
                    title,
                    query,
                )
            )

            ranked.append(
                (
                    score,
                    title,
                    video_id,
                )
            )

        ranked.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        print()
        print(
            "YouTube candidates:"
        )

        for item in ranked[:5]:

            print(
                f"  [{item[0]:+d}] "
                f"{item[1]}"
            )

        score, title, video_id = (
            ranked[0]
        )

        url = (
            "https://www.youtube.com/watch?v="
            + video_id
        )

        print(
            "Selected YouTube result:"
        )

        print(
            f"  Score: {score}"
        )

        print(
            f"  Title: {title}"
        )

        print(
            f"  URL: {url}"
        )

        return (
            url,
            title,
        )

    # ============================================================
    # NUDGE PLAYBACK
    # ============================================================

    def _nudge_youtube_playback(self):

        # Give the browser time to open, load the page, and get
        # focus before we send a keypress. Configurable in case
        # your machine/connection needs more or less time.

        delay = float(
            os.getenv(
                "YOUTUBE_AUTOPLAY_DELAY_SECONDS",
                "3.5",
            )
        )

        time.sleep(
            delay
        )

        try:

            import pyautogui

        except Exception as exc:

            print(
                "pyautogui is not available, "
                "could not nudge playback:",
                exc,
            )

            return

        try:

            # "k" is YouTube's own play/pause shortcut. It only
            # affects the page if the browser window/tab we just
            # opened has focus, which it should since we just
            # opened it.

            pyautogui.press(
                "k"
            )

            print(
                "Sent play keypress to YouTube."
            )

        except Exception as exc:

            print(
                "Could not send play keypress:",
                type(exc).__name__,
                exc,
            )

    # ============================================================
    # PLAY YOUTUBE
    # ============================================================

    def play_youtube(
        self,
        query,
    ):

        query = (
            self._clean_youtube_query(
                query
            )
        )

        if not query:

            return (
                "Which song or video would "
                "you like me to play on YouTube?"
            )

        print()
        print(
            "YouTube lookup:",
            query,
        )

        url, title = (
            self._find_youtube_video(
                query
            )
        )

        if url:

            try:

                # ------------------------------------------------
                # AUTOPLAY IS UNRELIABLE
                #
                # Chrome/Edge generally block unmuted autoplay for
                # a tab that was opened by an outside program
                # rather than a real click, so "&autoplay=1" often
                # gets ignored and the video just sits there
                # loaded but paused.
                #
                # So: open the video, give the page a moment to
                # finish loading, then send YouTube's own "play"
                # keyboard shortcut ('k') to actually start it.
                # ------------------------------------------------

                autoplay_url = (
                    url
                    + "&autoplay=1"
                )

                print(
                    "Opening YouTube video:",
                    title,
                )

                print(
                    "YouTube URL:",
                    autoplay_url,
                )

                opened = webbrowser.open(
                    autoplay_url,
                    new=2,
                )

                if opened:

                    self._nudge_youtube_playback()

                    return (
                        f"Playing {title} "
                        f"on YouTube."
                    )

                return (
                    f"I found {title}, "
                    "but I couldn't open YouTube."
                )

            except Exception as exc:

                print(
                    "YouTube open error:",
                    type(exc).__name__,
                    exc,
                )

        # --------------------------------------------------------
        # FALLBACK
        # --------------------------------------------------------

        self.search_youtube(
            query
        )

        return (
            f"I couldn't select a YouTube video "
            f"automatically, so I opened results "
            f"for {query}."
        )