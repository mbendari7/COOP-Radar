# CoopRadar: the simple guide

**CoopRadar helps you land a co-op.** Drop in your resume and it shows you:

- ✅ **What your resume is good at**: the skills employers can actually see on it
- 📈 **What you're missing**: the skills real job postings ask for most that your resume doesn't show
- 🎯 **How to tailor it**: an AI review with fixes, tailoring tips, and roles to search for
- 💼 **Which jobs to apply for**: real co-op, intern, and junior jobs from Canadian employers, ranked for you

No sign-up and no install. It's a website.

---

## 1. Get to the website

Pick the one that fits you:

| You are… | Do this |
|---|---|
| **A student** someone shared a link with | Just open the link. Skip to [section 2](#2-use-it-in-3-steps). |
| **The person sharing it** (you want your own copy online) | [Put it online in about 10 minutes](#put-your-own-copy-online-no-docker-no-coding) (free, no Docker, no coding) |
| **A developer** who wants it on your own computer | [Run it on your computer](#run-it-on-your-computer) |

### Put your own copy online (no Docker, no coding)

This uses **Render**, a hosting site with a free plan. Render builds everything on its own servers. You only click
buttons in your browser.

1. Make a free account at **https://render.com** by choosing **Sign up with GitHub**.
2. Go to the project's GitHub page and click the purple **Deploy to Render** button near the top of the README.
   (Or, in Render: **New → Blueprint**, then pick the `COOP-Radar` repository.)
3. Render lists what it will create: the website, a database, and a small cache. Click **Apply** (or
   **Deploy Blueprint**).
4. It asks for `ANTHROPIC_API_KEY` and `OPENAI_API_KEY`. **Leave both blank.** Visitors use their own free AI key.
5. Wait about 5–10 minutes for the first build. When it says **Live**, open the link at the top of the page. It looks
   like `https://coopradar-xxxx.onrender.com`.
6. In the first minute or two the site pulls in real jobs from about 27 employers' career pages. Refresh the
   **Jobs** page and you'll see hundreds of postings.

That link is your website. Share it with anyone.

> **About the free plan:** the site falls asleep after about 15 minutes with no visitors. The next visitor waits
> about a minute while it wakes up. Render's free database is also time-limited (about 30 days at the time of
> writing). Before an important demo or pitch, open the site yourself a minute early. For an always-on site,
> upgrade the web service and database to paid plans in Render (a few dollars a month). Check Render's pricing
> page for current details.

### Run it on your computer

You need **[Docker Desktop](https://www.docker.com/products/docker-desktop/)** installed and running.
Then, in a terminal:

```bash
git clone https://github.com/mbendari7/COOP-Radar.git
cd COOP-Radar
cp .env.example .env                                  # then open .env and set POSTGRES_PASSWORD to anything
docker compose -f docker-compose.prod.yml up --build
```

Open **http://localhost:8080**. The first start takes a few minutes. To stop it, press `Ctrl + C`.

---

## 2. Use it in 3 steps

### Step 1: Upload your resume
Click **My resume** (or **Analyze my resume** on the home page). Drag your resume onto the box, or click it to
choose a file (PDF or Word, up to 5 MB).

You don't need an account. The site makes you a **private temporary account** that's kept for 7 days. To keep it
for good, click **Keep my account** in the yellow bar and add an email and password. Everything stays.

### Step 2: Read what your resume says
Right away, for free:
- **Skills employers can see**: skills found on your resume that real postings ask for.
- **In demand, but not on your resume**: the skills open jobs ask for most, with how many jobs want each.

For the full picture, click **Get my AI review**. You'll need an AI key first ([how to get one free](#3-get-a-free-ai-key-optional)).
The review gives you:
- 💪 **What you're good at**, with evidence from your resume
- 🛠️ **What to fix**, like weak bullet points or missing numbers
- 🎯 **How to tailor it** for co-op applications
- 🔎 **Roles to search for**. Click one to search the jobs list.
- 🏷️ **Keywords to add**, but only ones that are true for you

### Step 3: Apply to the right jobs
Under **Jobs to apply for** you get your 20 best matches, each with a score out of 100 and a reason like
*"You have Python, SQL; it also asks for Go."* For each job:
- **✏️ Tailor my resume**: what to lead with, three bullet rewrites, keywords from the posting, and gaps to address
- **✉️ Cover letter opener**: a first paragraph written from your real experience
- **Ask a question**: for example "Do I have the skills for this?" Answers quote your resume or the posting.

Click the job title, then **Apply on the company's site**. CoopRadar never applies for you. It sends you to the
employer.

### Also handy
- **Jobs**: search everything. Filter by city (remote jobs always show up too), term, work mode, or skills.
  Tick **Co-op & intern roles only** to hide full-time senior roles. **Live** means the job came straight from the
  employer's careers page.
- **Tracker**: bookmark jobs, then move each one through *Applying → Applied → Interview → Offer*. You can add
  notes and dates, and you can export to a spreadsheet.
- **Try the demo**: opens a pre-filled sample account so you can see everything before uploading your own resume.

---

## 3. Get a free AI key (optional)

The skills check and job matches work **without** a key. The AI review, tailoring, cover letter openers, and
questions use **your own** AI account. That's how the site stays free.

**Easiest (free): Google Gemini**
1. Go to **https://aistudio.google.com/apikey** and sign in with a Google account.
2. Click **Create API key**, then copy it (it starts with `AIza`).
3. On CoopRadar, click **AI key** in the top bar, choose **Gemini**, paste it, click **Check key**, then
   **Use this key**.

<details>
<summary><b>ChatGPT (OpenAI) or Claude (Anthropic) instead</b></summary>

Both are pay-as-you-go. A full review plus a few tailoring requests usually costs a few cents.

**ChatGPT (OpenAI)**
1. Sign in at **https://platform.openai.com**. Add a little credit under **Settings → Billing**.
2. Create a key at **https://platform.openai.com/api-keys** and copy it right away (it starts with `sk-`).

**Claude (Anthropic)**
1. Sign in at **https://console.anthropic.com**. Add a little credit under **Settings → Billing**.
2. Go to **Settings → API keys → Create Key** and copy it right away (it starts with `sk-ant-`).

An API key is not the same as a ChatGPT Plus or Claude.ai subscription. Those are for chatting on their own
websites. API keys let apps like CoopRadar use the AI, and they're billed separately.
</details>

**Is my key safe?** Your key stays **in your browser**. The server passes it to your AI provider for each request
and never saves or logs it. By default it's forgotten when you close the tab. Tick **Remember on this device** to
keep it. For extra safety, set a monthly spending limit in your provider's dashboard.

---

## 4. Tips and tricks

- **Put a clear Skills section on your resume** (for example "Python, SQL, React, Git"). It's what both CoopRadar and
  real applicant-tracking systems scan for first.
- **Only add skills you really have.** The "in demand" list is a learning roadmap, not a list to paste in.
- **Use a text-based PDF.** If your resume is a scanned image, nothing can be read from it. Export it from Word or
  Google Docs as a PDF.
- **Upload a new version any time.** Edit your resume, upload again, and watch your matches and skills update.
- **Tailor the top 3–5 jobs, not all 20.** Use **Tailor my resume** on each, then save a copy of your resume per job.
- **Click the "Roles to search for" chips** from your AI review to find jobs you might not have searched for.
- **Re-rank with my AI**: once you've added a key, this button re-scores your matches with AI. It's smarter than
  the free skill match.
- **Check back weekly.** New jobs arrive every few hours. Co-op and intern roles come in waves before each term.
- **Bookmark early, track everything.** Deadlines this week show up at the top of your Tracker.
- **Always proofread AI text** before you send it. It's a strong first draft, not a final one.

---

## 5. Something not working?

| What you see | What to do |
|---|---|
| The site takes a minute to load | It was asleep (free hosting). Wait about a minute. It's quick after that. |
| "Could not extract text" | Your PDF is probably a scanned image. Export it again from Word or Google Docs. |
| "That file is over 5 MB" | Export a smaller PDF (remove images or photos). |
| No jobs in the list | On a brand-new site, jobs import in the first couple of minutes. Refresh. |
| "Add your own AI key…" | You haven't added a key in this browser yet. See [section 3](#3-get-a-free-ai-key-optional). |
| "…rejected the API key" | The key was copied wrong or deleted. Make a new one. |
| "…out of credit or over its rate limit" | Gemini's free tier limits requests per minute. Wait a minute and try again. |
| "Too many demo accounts from this network" | Wait an hour, or create a normal account. |
| My temporary account disappeared | Temporary accounts are deleted after 7 days. Next time, click **Keep my account**. |

---

## 6. Your privacy

- Your resume is stored **only in your account**. Delete it any time with **My resume → Delete**.
- It's only sent to the AI provider **you** choose, and only when you click an AI button.
- Temporary accounts are deleted automatically after 7 days unless you keep them.
- Jobs come from employers' **public** career pages (Greenhouse, Lever, Ashby job boards). Every job links back to
  the employer, and you always apply there.
