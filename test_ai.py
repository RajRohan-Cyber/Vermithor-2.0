from vermithor.audio.wakeword import WakeWord
from vermithor.audio.listener import VoiceListener
from vermithor.brain.ai import VermithorAI


print()
print("=" * 60)
print("              VERMITHOR SYSTEM TEST")
print("=" * 60)
print()


# =========================================================
# WAKE WORD
# =========================================================

print("[1/4] Testing wake-word engine...")

wake = WakeWord()

tests = [

    "Vermithor open Google",

    "vermiform open Google",

    "vermitor open Google",

    "vermithar open Google",

    "Varun Dhawan open Google",

    "Mithun open Google",

    "Ek Bar Mithun open Google",

    "hello there"
]

for text in tests:

    print()

    print(
        f"Input: {text}"
    )

    print(
        f"Wake detected: "
        f"{wake.detected(text)}"
    )

    print(
        f"Command: "
        f"{wake.remove_wake_word(text)}"
    )


print()

print(
    "[1/4] Wake-word engine: OK"
)


# =========================================================
# LISTENER
# =========================================================

print()

print(
    "[2/4] Testing voice listener import..."
)

listener = VoiceListener()

print(
    "[2/4] Voice listener: OK"
)


# =========================================================
# AI
# =========================================================

print()

print(
    "[3/4] Testing Ollama..."
)

try:

    ai = VermithorAI()

    print(
        f"[3/4] Ollama: OK"
    )

    print(
        f"      Model: {ai.model}"
    )

except Exception as error:

    print(
        "[3/4] Ollama: FAILED"
    )

    print(
        error
    )


# =========================================================
# STRUCTURE
# =========================================================

print()

print(
    "[4/4] Vermithor core imports: OK"
)

print()

print("=" * 60)

print(
    "SYSTEM TEST FINISHED"
)

print("=" * 60)

print()