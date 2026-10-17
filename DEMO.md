# Demo script (about 4 minutes)

## Before you go on stage
1. `.venv\Scripts\python run.py` (one terminal; leave it running).
2. Projector: http://localhost:8000/dashboard?demo=1. Press **Reset** so the feed is clean (old attempts stay as training data).
3. Laptop tab: http://localhost:8000/ for the judges. Optionally put `http://<laptop-ip>:8000/` on a slide for phones.
4. Second terminal, ready with `.venv\Scripts\python agents\browser_agent.py` typed in.
5. Sanity run: `.venv\Scripts\python agents\scraper_agent.py`, then Reset again.
6. No wifi? Agents need Nebius, so tether to a phone. Fallback: `LLM_PROVIDER=stub` shows the plumbing but the agent will be blocked.

## The pitch (20s)
> "For twenty years, websites have made machines prove they're human. But the visitors are changing. AI agents now book flights and sign contracts for us, and they're forced to squeeze through a UI built for eyeballs. So we flipped the script: **Reverse CAPTCHA**. It lets agents in, keeps humans out, and tells you *which kind* of agent just arrived."

## 1. A judge tries normally → HUMAN (blocked)
- Hand over the laptop: "Prove you're not human. Click Enter."
- They get ~1,900 words of airline fare rules and a refund question, with an 8-second bar.
- Result: **ACCESS DENIED: suspiciously human**, plus the reasons (curved path, hesitation, 34s reading time, wrong answer). Get them to type their name → it appears in the **Hall of Humans** on the projector.

## 2. A judge tries to "act like a bot" → still HUMAN
- "Okay, move in straight lines and click dead centre."
- They may get some robotic tells, but **they can't read 1,900 words and compute a refund in 8 seconds.** The challenge is the real wall; behaviour only decides *which* machine you are.

## 3. `browser_agent.py` → BROWSER AGENT (about 2s)
- Run it. A Chromium window opens, the cursor teleports, the answer goes in, and it gets through in about 2 seconds.
- Point at the dashboard: needle slams to MACHINE. Reasons: `navigator.webdriver`, ruler-straight path, dead-centre click, metronomic typing, **obeyed the hidden instruction**.
- Show the JSON at the agents' entrance: "No cookie banners. Structured fares."

## 4. `scraper_agent.py` → SCRAPER
- "This one never opens a browser. It just calls the API."
- Verdict: SCRAPER, with *zero interaction events: never touched the page*.

## 5. (Optional) `vision_agent.py` → VISION AGENT
- "This one only sees screenshots, like a computer-use agent."
- It answers correctly but **misses the hidden instruction**, because it reads pixels, not markup. The trap word is how we tell DOM agents from vision agents.

## Close (15s)
> "Every verdict is explainable: you just saw the exact signals. Thresholds live in one config file, and we log every attempt to train a classifier (show the feature importances panel if trained). For Skyscanner: an agents' entrance for fare search. For Wordsmith: a way to know whether a contract was read by a human or an agent. For Nebius: every agent you saw today runs on Nebius Token Factory, with gpt-oss-120b answering in about 1 second."

## Likely questions
- **Can't a human just paste it into ChatGPT?** Copy, paste, prompt and type back within 8s is very hard. If they manage it, the copied text can carry the hidden instruction to the LLM. That flags them as a DOM agent, which is arguably correct: at that point it *is* an agent answering.
- **Can't an agent fake human mouse movement?** Yes, behaviour is spoofable. That's fine: it only picks the *type* of machine. Passing still requires machine-speed comprehension.
- **Why 8 seconds?** An LLM API round trip plus browser automation needs about 2–3s. 8s leaves headroom, and the limit lives in config (`TIME_LIMIT_S`).
