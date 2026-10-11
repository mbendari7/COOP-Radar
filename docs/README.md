# Start Here: Run It, Understand It, Explain It

This is the one page to read first. It's written in plain language for whoever owns this project.
Every other guide is linked at the bottom when you want more detail.

---

## 1. What CoopRadar is (in one breath)

A website where students **find co-op/internship postings**, **track their applications**, and **match their
resume with AI**. The AI part runs on the **visitor's own AI key** (Claude, ChatGPT, or Gemini), so the person
hosting the site pays nothing for AI.

---

## 2. Run it on your computer (about 5 minutes)

You need one program: **Docker Desktop** (https://www.docker.com/products/docker-desktop/). Install it, open it,
and wait until it says *Engine running*.

Then, in a terminal (PowerShell on Windows) inside the project folder:

```powershell
# 1. Create your settings file (only the first time)
cp .env.example .env
#    Open .env and set POSTGRES_PASSWORD to any password. You don't need any AI keys.

# 2. Start the whole website
docker compose -f docker-compose.prod.yml up --build
```

Wait until you see `Starting web server on port 8000`, then open **http://localhost:8080**.

That's it. On startup the app creates the database, loads 55 sample postings, and starts its background worker.
To stop it, press `Ctrl+C`. Next time, just run step 2 again; your data is kept.

### Try everything in 2 minutes
1. **Browse**: search `python`, add filters, and sort. Everything you choose is saved in the URL.
2. **Try the demo**: click the button. You get a private account with sample applications and resume matches,
   no sign-up needed.
3. **Saved**: change an application's status, drag cards on the **Board**, and download a CSV.
4. **AI key**: click **AI key** at the top and follow the steps (Gemini has a free tier). Paste your key, press
   **Check key**, then **Use this key**.
5. **Matches**: upload your own resume (PDF or DOCX). Your AI ranks your top 20 postings. Click
   **Ask about this role** and ask "What skills am I missing?"

---

## 3. How it works (the simple version)

```
Visitor's browser ──► CoopRadar website + API (one container) ──► PostgreSQL database
       │                        │                                  (postings, accounts, tracker)
       │  their AI key          ├──► Redis (logins, background job queue)
       └───────────────────────►└──► Their AI provider (Claude / ChatGPT / Gemini)
```

| Part | What it does | Where it lives |
|---|---|---|
| **Website** (React) | The pages you click on | `frontend/src/` |
| **API** (FastAPI, Python) | Receives every request, checks who you are, runs the logic | `backend/app/` |
| **Database** (PostgreSQL) | Stores postings, users, saved applications, resumes. It also does the searching. | `backend/app/models/` |
| **Redis** | Remembers who's logged in; holds background jobs | — |
| **Worker** | Fetches job feeds every 6 hours in the background | `backend/app/worker.py` |
| **AI** | Ranks postings against a resume and answers questions, on the visitor's key | `backend/app/ai.py` |

### What happens when someone matches their resume
1. They upload a resume. The server pulls out the text (it never keeps the file).
2. **Shortlist (no AI):** the database finds the 40 open postings whose required skills best overlap the resume.
3. **AI ranking:** the server sends the resume plus those 40 postings to *the visitor's* AI with their key,
   asking "score each 0–100 and say why." It keeps the top 20.
4. **Safety checks:** it throws away any posting the AI made up and keeps scores between 0 and 100. If the AI
   reply is unusable, it falls back to the shortlist order.
5. **Questions:** "Ask about this role" sends the resume and posting to their AI with strict rules: answer only
   from these two texts, label each claim `Resume:` or `Posting:`, and say *"I don't have enough information"*
   when the answer isn't there. The reply appears word by word as it's written.

### Where the visitor's AI key goes
It's saved **only in their browser**. With each AI request it travels over HTTPS to the server, which hands it to
their provider for that one request. It is **never saved or logged** on the server.

---

## 4. How to explain it (interview-ready)

**30 seconds:**
> "CoopRadar is a full-stack web app that brings co-op postings into one searchable place, lets students track
> applications on a board, and matches their resume using AI. It's React + TypeScript on the frontend and FastAPI
> + PostgreSQL on the backend. Postgres does the full-text search and fuzzy duplicate detection itself. The AI is
> bring-your-own-key: users plug in a Claude, ChatGPT, or Gemini key, the database shortlists postings by skills,
> and their model ranks and explains the matches. It ships as one Docker container with a CI pipeline that tests
> everything, including a production smoke test."

**Questions you'll likely get:**

| They ask | You answer |
|---|---|
| Why bring-your-own-key? | Hosting is free for me, users control their own spending and data, and they can pick the provider they trust. |
| Is the key safe? | It stays in their browser and is forwarded per request over HTTPS. The server never stores or logs it, and error messages never include it. |
| Why shortlist before the AI? | The database can scan every posting instantly for free. The AI is slower and costs money, so it only judges the best 40. |
| How do you stop the AI making things up? | It answers only from the resume and posting, must label its sources, and must say "not enough information". The server also drops any posting the AI invents. |
| How do you support three AI companies? | One small module (`app/ai.py`) gives the app a single "complete" and "stream" function; inside, it talks to each provider's official SDK and turns their errors into the same clear messages. |
| How do you know it works? | 200 automated tests (backend + frontend), strict type checking, and CI that also builds the production container and smoke-tests it on every push. |

---

## 5. Common problems

| Problem | Fix |
|---|---|
| `docker` not found / can't connect | Open Docker Desktop and wait for *Engine running*. |
| "port is already allocated" | Something else uses port 8080. Set `APP_PORT=8081` in `.env` and open http://localhost:8081. |
| Matches says "Add your AI key" | Click **AI key** and add one (section 2, step 4). |
| "rejected the API key" | The key was copied wrong or deleted. Create a new one and check it again. |
| "out of credit or over its rate limit" | Add credit in your provider's dashboard, or wait a minute (free tiers have per-minute limits). |
| Want a completely fresh start | `docker compose -f docker-compose.prod.yml down -v` (deletes all data), then start again. |

---

## 6. All the guides

| Guide | Read it to… |
|---|---|
| [AI_KEYS.md](AI_KEYS.md) | Get a Claude, ChatGPT, or Gemini API key, step by step |
| [GETTING_STARTED.md](GETTING_STARTED.md) | Use every feature in detail, and run the developer setup |
| [HOW_IT_WORKS.md](HOW_IT_WORKS.md) | Follow each feature step by step through the code |
| [DEPLOY.md](DEPLOY.md) | Put the website on the internet |
| [PROJECT_GUIDE.md](PROJECT_GUIDE.md) | Go deep: every module, the database, testing, recipes for changes |

Project records: [agentic-workflow.md](agentic-workflow.md) (AI-assisted work log) ·
[progress.md](progress.md) (status) · [speckit-prompts.md](speckit-prompts.md) (feature prompts) ·
[history/](history/) (original setup). Feature specs are in [`../specs/`](../specs/).
