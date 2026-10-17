# Demo script (about 4 minutes)

## Before you go on stage
1. `.venv\Scripts\python run.py` (one terminal; leave it running).
2. Projector: http://localhost:8000/dashboard?demo=1. Press **Reset** so the feed is clean (old attempts stay as training data). Reset only works from the laptop running the server, so the audience can't wipe the feed.
3. Laptop tabs: http://localhost:8000/ (gate) and http://localhost:8000/flights (flight site) for the judges. Optionally put `http://<laptop-ip>:8000/` on a slide for phones.
4. Second terminal, ready with `.venv\Scripts\python agents\browser_agent.py` typed in.
5. Sanity run: `.venv\Scripts\python agents\scraper_agent.py`, then Reset again.
6. No wifi? Agents need Nebius, so tether to a phone. Fallback: `LLM_PROVIDER=stub` shows the plumbing but the agent will be blocked.

## The pitch (20s)
> "For twenty years, websites have made machines prove they're human. But the visitors are changing. AI agents now book flights and sign contracts for us, and they're forced to squeeze through a UI built for eyeballs. So we flipped the script: **Reverse CAPTCHA**. It lets agents in, keeps humans out, and tells you *which kind* of agent just arrived."

## 1. A judge tries normally → HUMAN (blocked)
- Hand over the laptop: "Prove you're not human. Just tick the box."
- The checkbox silently checks how they moved. Result: **ACCESS DENIED: suspiciously human**, with the reasons (curved path, hesitation, sloppy click). No wall of text.
- The consolation prize is a picker for the four demo sites (flights, contracts, tickets, shop). Let them click one and use it normally. They're never challenged.

## 2. A judge tries to "act like a bot" → still HUMAN
- Press **"Think you can pass as a machine? Try the 6-second test"** on the picker.
- They get ~1,900 words of airline fare rules and a refund question, with a 6-second bar. **No human can read that and compute a refund in 6 seconds.** The challenge is the real wall; behaviour only decides *which* machine you are.
- Get them to type their name → it appears in the **Hall of Humans** on the projector.
- (Agents never see the picker: when the checkbox flags machine-like behaviour, the visitor goes straight to the challenge, which also works out *which kind* of agent it is.)

## 3. `browser_agent.py` → BROWSER AGENT (about 2s)
- Run it. A Chromium window opens, the cursor teleports, the answer goes in, and it gets through in about 2 seconds.
- Point at the dashboard: needle slams to MACHINE. Reasons: `navigator.webdriver`, ruler-straight path, dead-centre click, metronomic typing, **obeyed the hidden instruction**.
- Show the JSON at the agents' entrance: "No cookie banners. Structured fares."

## 4. `scraper_agent.py` → SCRAPER
- "This one never opens a browser. It just calls the API."
- Verdict: SCRAPER, with *zero interaction events: never touched the page*.

## 4b. The real-world version: invisible rerouting on a flight site (`/flights`)
- "Nobody wants a CAPTCHA when booking a holiday. So on a real site it's invisible."
- Search as a human at http://localhost:8000/flights → normal results. No challenge.
- Run `.venv\Scripts\python agents\flight_agent.py` → same page, same button. It gets **"Agent detected → agent lane"** and lands on `/agents/search` with its search intact. gpt-oss then picks the cheapest direct flight from the JSON.
- Run `curl -L "http://127.0.0.1:8000/flights/results?from=EDI&to=KEF"` → a script is rerouted before any HTML is rendered.
- Point at the **Flight search lanes** panel: "Agent traffic is on its own lane, so it never slows down real travellers. The gate you saw earlier becomes the step-up check for unclear cases."

## 4c. Same idea, other industries (`/sites`), about 1 minute
Open http://localhost:8000/sites, then run one or two of these, depending on which judge you're talking to:
- **Wordsmith (legal):** `.venv\Scripts\python agents\site_agent.py contracts`. The agent gets rerouted, gpt-oss flags clauses 3, 4 and 7 as risky, and it signs **on behalf of** its principal. The site records a *delegated agent signature* and returns `pending_human_countersign` because clause 7 is high risk. "You always know whether a human or an agent signed, and on whose behalf."
- **Ticketing:** `.venv\Scripts\python agents\site_agent.py tickets`. It reserves 2 tickets, then tries to scalp 4 more and gets **429 quota**. "Bots get their own queue and can't crowd out fans."
- **Shopping:** `.venv\Scripts\python agents\site_agent.py shop`. It buys the limited drop, then tries a second pair and gets **429 drop limit**.
- The dashboard's **Human vs agent lanes** panel shows every reroute with a site icon.

## 5. (Optional) `vision_agent.py` → VISION AGENT
- "This one only sees screenshots, like a computer-use agent."
- It answers correctly but **misses the hidden instruction**, because it reads pixels, not markup. The trap word is how we tell DOM agents from vision agents.

## Close (15s)
> "Every verdict is explainable: you just saw the exact signals. Thresholds live in one config file, and we log every attempt to train a classifier (show the feature importances panel if trained). For Skyscanner: an agents' entrance for fare search. For Wordsmith: a way to know whether a contract was read by a human or an agent. For Nebius: every agent you saw today runs on Nebius Token Factory, with gpt-oss-120b answering in about 1 second."

## Likely questions
- **Can't a human just paste it into ChatGPT?** Copy, paste, prompt and type back within 6s is very hard. If they manage it, the copied text can carry the hidden instruction to the LLM. That flags them as a DOM agent, which is arguably correct: at that point it *is* an agent answering.
- **Can't an agent fake human mouse movement?** Yes, behaviour is spoofable. That's fine: it only picks the *type* of machine. Passing still requires machine-speed comprehension.
- **Why 6 seconds?** Our agents take about 2s (text) and about 4–5s (vision, which also gets a configurable grace window). 6s leaves headroom, and the limit lives in config (`TIME_LIMIT_S`).
