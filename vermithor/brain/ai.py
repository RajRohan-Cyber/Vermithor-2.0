import os

import ollama

from dotenv import load_dotenv


load_dotenv()


class VermithorAI:

    """
    Vermithor's local reasoning layer.

    Memory is intentionally separate from the AI.
    """

    def __init__(
        self,
        memory=None
    ):

        self.model = os.getenv(
            "OLLAMA_MODEL",
            "llama3.2:3b"
        )

        self.host = os.getenv(
            "OLLAMA_HOST",
            "http://127.0.0.1:11434"
        )

        self.memory = memory

        self.client = ollama.Client(
            host=self.host
        )

        self.history = []

        self.system_prompt = (

            "You are Vermithor, "
            "Rohan's local Windows desktop assistant. "

            "Be concise, natural, intelligent "
            "and helpful. "

            "Answer normal questions directly. "

            "Never claim that a computer action "
            "was performed unless the action system "
            "actually performed it. "

            "Do not mention your internal architecture "
            "unless Rohan asks."
        )

    # ==========================================================
    # ASK
    # ==========================================================

    def ask(
        self,
        user_text
    ):

        user_text = str(
            user_text or ""
        ).strip()

        if not user_text:
            return ""

        system = (
            self.system_prompt
        )

        # ------------------------------------------------------
        # MEMORY
        # ------------------------------------------------------

        if self.memory:

            facts = (
                self.memory.get_facts()
            )

            if facts:

                system += (
                    "\nKnown facts about Rohan:\n"
                )

                system += "\n".join(

                    f"- {fact}"

                    for fact in facts[-20:]

                )

        # ------------------------------------------------------
        # MESSAGES
        # ------------------------------------------------------

        messages = [

            {
                "role": "system",
                "content": system
            }

        ]

        messages.extend(
            self.history[-8:]
        )

        messages.append(

            {
                "role": "user",
                "content": user_text
            }

        )

        # ------------------------------------------------------
        # OLLAMA
        # ------------------------------------------------------

        try:

            response = (
                self.client.chat(

                    model=self.model,

                    messages=messages,

                    options={

                        "temperature": 0.35,

                        "num_ctx": 4096,

                        "num_predict": 300
                    }
                )
            )

            answer = str(

                response
                .get(
                    "message",
                    {}
                )
                .get(
                    "content",
                    ""
                )

            ).strip()

            if not answer:

                return (
                    "I couldn't generate "
                    "a response."
                )

            # --------------------------------------------------
            # HISTORY
            # --------------------------------------------------

            self.history.extend(

                [

                    {
                        "role": "user",
                        "content": user_text
                    },

                    {
                        "role": "assistant",
                        "content": answer
                    }

                ]

            )

            # --------------------------------------------------
            # MEMORY
            # --------------------------------------------------

            if self.memory:

                self.memory.add_conversation(

                    user_text,

                    answer
                )

            return answer

        except Exception:

            return (

                "I can't reach the local "
                "Ollama AI right now. "

                "Please make sure Ollama "
                "is running."
            )

    # ==========================================================
    # CLEAR HISTORY
    # ==========================================================

    def clear_history(
        self
    ):

        self.history.clear()