# Quickstart: Bring Your Own AI Key and a Resume First Site

How to try this feature by hand.

## Run the site

```bash
python start.py
```

Open http://localhost:8000. No `.env` needed. Let the importer bring in some jobs first (watch the terminal) or
start with `SEED_SAMPLE_POSTINGS=true` for 55 made up ones.

## 1. Matches with no account and no key

1. Open a private window so you are signed out
2. Go to Match my resume and drop a text PDF or DOCX that has a Skills line
3. You should see skills found, skills worth adding and a list of matches, each with a reason
4. The header shows a temporary account strip with Keep my account

## 2. Your own AI key

1. Open AI key, pick a provider and follow the steps to get a key
2. Paste it and click Check. A model list shows with one picked
3. Back on Match my resume, click Get my AI review. A summary, strengths and improvements appear
4. Click Re-rank with my AI. The scores change and the reasons get more specific
5. On a match, click Tailor my resume, Write a cover letter, or ask a question. The answer streams in
6. Ask something the posting does not say, like the salary. The answer should be "I don't have enough information
   to answer that."

## 3. Bad keys

1. Paste `sk-ant-not-a-real-key` and click Check. It says the key was rejected and does not show it back
2. Do the same for ChatGPT and Gemini

## 4. Demo account

1. Sign out and click Try the demo
2. The tracker has cards in several columns and the resume page has matches
3. Click Keep my account, enter an email and a password of 10 or more characters

## 5. Owner key with a limit

```bash
ANTHROPIC_API_KEY=... AI_DAILY_LIMIT=2 python start.py
```

With no visitor key, run three AI actions. The third says the daily limit is reached.

## Tests for this feature

```bash
cd backend
pytest -q tests/api/test_ai.py tests/api/test_guest.py tests/resume tests/eval
cd ../frontend
npm test -- aiKey ResumePage RichText DemoButton
```
