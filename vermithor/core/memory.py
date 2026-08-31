import json
import os
from pathlib import Path


class Memory:

    def __init__(self, filename=None):

        root = Path(__file__).resolve().parents[2]

        self.filename = Path(
            filename
            or os.getenv(
                "MEMORY_FILE",
                str(root / "data" / "memory.json")
            )
        )

        self.filename.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        if not self.filename.exists():

            self._save({
                "facts": [],
                "conversation": []
            })


    def _load(self):

        try:

            data = json.loads(
                self.filename.read_text(
                    encoding="utf-8"
                )
            )

            if not isinstance(data, dict):
                raise ValueError()

            data.setdefault(
                "facts",
                []
            )

            data.setdefault(
                "conversation",
                []
            )

            return data

        except Exception:

            return {
                "facts": [],
                "conversation": []
            }


    def _save(self, data):

        self.filename.write_text(
            json.dumps(
                data,
                indent=2,
                ensure_ascii=False
            ),
            encoding="utf-8"
        )


    def remember(self, fact):

        fact = fact.strip()

        if not fact:
            return

        data = self._load()

        if fact not in data["facts"]:

            data["facts"].append(
                fact
            )

        data["facts"] = data["facts"][-100:]

        self._save(data)


    def get_facts(self):

        return self._load()["facts"]


    def add_conversation(
        self,
        user,
        assistant
    ):

        data = self._load()

        data["conversation"].append(
            {
                "user": user,
                "assistant": assistant
            }
        )

        data["conversation"] = data[
            "conversation"
        ][-50:]

        self._save(data)


    def get_conversation(self):

        return self._load()["conversation"]


    def clear(self):

        self._save(
            {
                "facts": [],
                "conversation": []
            }
        )