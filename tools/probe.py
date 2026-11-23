import sys
from assistant import brain

for text in sys.argv[1:] or [line.strip() for line in sys.stdin if line.strip()]:
    a = brain.analyze_intent(text)
    print(f"{text!r:45} -> {a['intent']:26} {a['group']:8} {a['source']:10} {a['confidence']:.2f}")