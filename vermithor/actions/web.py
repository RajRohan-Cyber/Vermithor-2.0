import webbrowser


class WebActions:

    def open(self, url):

        if not url.startswith(
            ("http://", "https://")
        ):
            url = "https://" + url

        webbrowser.open(url)

        return f"Opened {url}."