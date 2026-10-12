"""WhatsApp Support Agent core: classify -> retrieve -> answer or hand over."""
import argparse
import json
import re
from datetime import datetime
from pathlib import Path

import llm

INTENTS = {
    "complaint": ["not happy", "complain", "terrible", "refund", "wrong item", "damaged", "angry", "scam"],
    "order_status": ["order", "where is my", "track", "status", "delivered yet"],
    "price": ["price", "how much", "cost"],
    "delivery": ["deliver", "shipping", "lagos", "abuja", "how long"],
    "returns": ["return", "exchange"],
    "greeting": ["hello", "hi", "good morning", "good afternoon"],
}

FAQ = json.loads(Path(__file__).with_name("faq.json").read_text())
ORDERS = json.loads(Path(__file__).with_name("orders.json").read_text())


def classify(text: str) -> str:
    t = text.lower()
    for intent, words in INTENTS.items():
        if any(w in t for w in words):
            if intent == "order_status" and not re.search(r"\b(?:ord|#)?\s*-?\d{4,}\b", t) \
                    and "where is my" not in t:
                continue
            return intent
    guess = llm.complete(f"Classify this customer message into one of {list(INTENTS)} or "
                         f"'unknown'. Reply with one word.\n\n{text}")
    return guess.strip().lower() if guess and guess.strip().lower() in INTENTS else "unknown"


def retrieve(text: str, intent: str):
    words = set(re.findall(r"[a-z]+", text.lower()))
    best, best_score = None, 0
    for item in FAQ:
        if item["intent"] != intent:
            continue
        s = len(words & set(item["keywords"]))
        if s > best_score:
            best, best_score = item, s
    if best is None:
        candidates = [i for i in FAQ if i["intent"] == intent]
        best = candidates[0] if candidates else None
    return best


def handle(msg: dict) -> dict:
    text, intent = msg["text"], classify(msg["text"])
    reply, handover = None, False
    if intent == "order_status":
        m = re.search(r"(\d{4,})", text)
        order = ORDERS.get(m.group(1)) if m else None
        if order:
            reply = (f"Order {m.group(1)} is {order['status']}"
                     + (f", expected {order['eta']}." if order.get("eta") else "."))
        else:
            reply = "Please send your order number (e.g. 10234) and I'll check it right away."
    elif intent in ("complaint", "unknown"):
        handover = True
        reply = ("I'm sorry about this. I've passed your message to a member of our team, "
                 "who will reply shortly.")
    elif intent == "greeting":
        reply = "Hi! How can we help today? You can ask about prices, delivery or your order."
    else:
        item = retrieve(text, intent)
        reply = item["answer"] if item else None
        handover = item is None
    return {"from": msg["from"], "text": text, "intent": intent, "reply": reply,
            "handover": handover, "at": datetime.now().isoformat(timespec="seconds")}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", default="sample_messages.json")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    msgs = json.loads(Path(a.input).read_text())
    results = [handle(m) for m in msgs]
    Path("output").mkdir(exist_ok=True)
    Path("output/handover_queue.json").write_text(
        json.dumps([r for r in results if r["handover"]], indent=2))
    for r in results:
        tag = "HANDOVER" if r["handover"] else "AUTO"
        print(f"[{r['intent']:<12}|{tag:<8}] {r['from']}: {r['text']}")
        print(f"   -> {r['reply']}\n")
    auto = sum(not r["handover"] for r in results)
    print(f"Answered automatically: {auto}/{len(results)}. Handover queue -> output/handover_queue.json")


if __name__ == "__main__":
    main()
