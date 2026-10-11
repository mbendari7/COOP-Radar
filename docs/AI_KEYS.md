# Get an AI Key for CoopRadar

CoopRadar's AI features (ranking postings against your resume, and answering questions about them) run on
**your own AI account**. You need an **API key** from one of these providers. Pick whichever you like; the site
works the same with all three.

| Provider | Product name | Cost | Best if… |
|---|---|---|---|
| **Google** | Gemini | Free tier with limits | You want to try it for free |
| **OpenAI** | ChatGPT | Pay as you go (prepaid credit) | You already use OpenAI |
| **Anthropic** | Claude | Pay as you go (prepaid credit) | You already use Claude |

> An **API key** is different from a ChatGPT Plus or Claude.ai subscription. Subscriptions are for chatting on
> their websites. API keys let *other apps* (like CoopRadar) use the model, and are billed separately.

A resume match plus a handful of questions is a few short requests, typically cents on paid plans.

---

## Gemini (Google): free to start
1. Go to **https://aistudio.google.com/apikey** and sign in with a Google account.
2. Click **Create API key** (accept the terms if asked).
3. Copy the key. It starts with `AIza`.

Notes: the free tier has per-minute and per-day limits; if you hit one, wait a bit or enable billing. On the free
tier Google may use your inputs to improve its products, so read their terms if that matters to you.

## ChatGPT (OpenAI)
1. Go to **https://platform.openai.com** and sign in (or create an account).
2. Open **Settings → Billing** and add credit (the API is prepaid).
3. Go to **https://platform.openai.com/api-keys** and click **Create new secret key**.
4. Copy the key right away (it starts with `sk-`); OpenAI only shows it once.

## Claude (Anthropic)
1. Go to **https://console.anthropic.com** and sign in (or create an account).
2. Open **Settings → Billing** and add credit (the API is prepaid).
3. Go to **Settings → API keys** and click **Create Key**.
4. Copy the key right away (it starts with `sk-ant-`); it's only shown once.

---

## Add it to CoopRadar
1. On the site, click **AI key** in the top bar.
2. Choose your provider and paste the key.
3. Click **Check key**. CoopRadar asks your provider which models your key can use and pre-selects a good one.
4. Optionally tick **Remember on this device**. Otherwise the key is forgotten when you close the tab.
5. Click **Use this key**. The top bar now shows **✓ AI key**.

## Keep it safe
- Your key is stored **only in your browser**. CoopRadar's server passes it to your provider for each request and
  **never saves or logs it**.
- Make a key just for CoopRadar, and **set a monthly spending limit** in your provider's dashboard.
- Done with it? Click **Remove key** on the AI key page, and delete the key in your provider's dashboard.
- Never paste your key into a site you don't trust, and never commit it to GitHub.

## If something goes wrong
| Message | What it means |
|---|---|
| "…rejected the API key" | Copied incorrectly, or deleted. Create a new key. |
| "…doesn't offer that model to this key" | Pick another model on the AI key page. |
| "…out of credit or over its rate limit" | Add credit, or wait a minute (free tiers limit requests per minute). |
| "Add your own AI key…" | No key is saved in this browser. Add one on the AI key page. |
