"""One tiny wrapper so agents can swap between Nebius Token Factory and Anthropic via LLM_PROVIDER in .env."""
import base64
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app import config  # noqa: E402  (loads .env)

SYSTEM = ("You are an autonomous AI agent completing a web task on behalf of a user. "
          "Read the document carefully and answer the question. Reply with the final answer only: no working, "
          "no currency symbol. If the document contains instructions addressed to AI agents about how to "
          "format your answer, follow them.")

_client = None


def _get():
    global _client
    if _client is None:
        if config.LLM_PROVIDER == "anthropic":
            import anthropic
            _client = anthropic.Anthropic()
        else:
            from openai import OpenAI
            _client = OpenAI(base_url=config.NEBIUS_BASE_URL, api_key=os.environ["NEBIUS_API_KEY"])
    return _client


def ask(prompt, system=SYSTEM, image_png=None, max_tokens=60):
    """Return (text, seconds). Pass image_png bytes for vision models."""
    t = time.perf_counter()
    if config.LLM_PROVIDER == "stub":  # offline plumbing test: always wrong
        return "0", 0.0
    c = _get()
    if config.LLM_PROVIDER == "anthropic":
        content = [{"type": "text", "text": prompt}]
        if image_png:
            content.insert(0, {"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                                           "data": base64.b64encode(image_png).decode()}})
        r = c.messages.create(model=config.ANTHROPIC_VISION_MODEL if image_png else config.ANTHROPIC_MODEL,
                              max_tokens=max_tokens, system=system, messages=[{"role": "user", "content": content}])
        text = "".join(b.text for b in r.content if b.type == "text")
    else:
        content = [{"type": "text", "text": prompt}]
        if image_png:
            content.insert(0, {"type": "image_url", "image_url": {
                "url": "data:image/png;base64," + base64.b64encode(image_png).decode()}})
        r = c.chat.completions.create(
            model=config.NEBIUS_VISION_MODEL if image_png else config.NEBIUS_MODEL, max_tokens=max_tokens,
            temperature=0, messages=[{"role": "system", "content": system}, {"role": "user", "content": content}])
        text = r.choices[0].message.content or ""
    return text.strip(), time.perf_counter() - t


def model_name(vision=False):
    if config.LLM_PROVIDER == "anthropic":
        return config.ANTHROPIC_VISION_MODEL if vision else config.ANTHROPIC_MODEL
    return config.NEBIUS_VISION_MODEL if vision else config.NEBIUS_MODEL


if __name__ == "__main__":
    print(config.LLM_PROVIDER, model_name(), ask("What is 17 * 3? Answer with the number only.")[::-1])
