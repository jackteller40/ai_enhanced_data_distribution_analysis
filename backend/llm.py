"""LLM explanation generator using Anthropic claude-haiku."""
import os
import anthropic
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


def generate_explanation(receiver: dict, candidate: dict) -> str | None:
    """Generate a one-sentence match explanation. Returns None on any failure."""
    try:
        shared_clubs = set(receiver.get("clubs") or []) & set(candidate.get("clubs") or [])
        shared_interests = set(receiver.get("interests") or []) & set(candidate.get("interests") or [])

        context_parts = []
        if shared_clubs:
            context_parts.append(f"both in {', '.join(shared_clubs)}")
        if shared_interests:
            context_parts.append(f"both enjoy {', '.join(shared_interests)}")
        if receiver.get("major") == candidate.get("major"):
            context_parts.append(f"both studying {candidate.get('major')}")
        if receiver.get("likes_going_out") == candidate.get("likes_going_out"):
            vibe = "love going out" if candidate.get("likes_going_out") else "prefer staying in"
            context_parts.append(f"both {vibe}")

        context = ", ".join(context_parts) if context_parts else "similar vibes"

        prompt = (
            f"Write one short, friendly sentence (in the first person) explaining why two Marist students "
            f"might hit it off. They have {context}. "
            f"Sound natural and warm, not robotic. Under 20 words."
        )

        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=60,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text.strip()

    except Exception as e:
        print(f"LLM explanation failed: {e}")
        return None