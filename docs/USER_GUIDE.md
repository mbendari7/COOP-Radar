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
| **The person sharing it** (you want your own copy online) | [Put it online in about 10 minutes](#put-your-own-copy-online-no-coding) (free, no coding) |
| **Anyone** who wants it on their own computer | [Run it on your computer](#run-it-on-your-computer) (one command) |

### Put your own copy online (no coding)

This uses **Render**, a hosting site with a free plan. Render builds everything on its own servers. You only click
buttons in your browser.

1. Make a free account at **https://render.com** by choosing **Sign up with GitHub**.
2. Go to the project's GitHub page and click the purple **Deploy to Render** button near the top of the README.
   (Or, in Render: **New → Blueprint**, then pick the `COOP-Radar` repository.)
3. Render lists what it will create: the website and a database. Click **Apply** (or
   **Deploy Blueprint**).
4. It asks for `ANTHROPIC_API_KEY` and `OPENAI_API_KEY`. **Leave both blank.** Visitors use their own free AI key.
5. Wait about 5–10 minutes for the first build. When it says **Live**, open the link at the top of the page. It looks
   like `https://coopradar-xxxx.onrender.com`.
6. In the first minute or two the site pulls in real jobs from about 27 employers' career pages. Refresh the
   **Jobs** page and you'll see hundreds of postings.

That link is your website. Share it with anyone.

**Want a Vercel address instead (`your-site.vercel.app`)?** Do the Render steps first (Render runs the part with
the database). Then sign in at **https://vercel.com** with GitHub, click **Add New, Project**, pick `COOP-Radar`
and click **Deploy**. Vercel shows the pages and quietly passes every `/api` request on to your Render site. If
your Render address isn't `https://coopradar.onrender.com`, change that address in `vercel.json` first. Details in
`docs/DEPLOY.md`.

> **About the free plan:** the site falls asleep after about 15 minutes with no visitors. The next visitor waits
> about a minute while it wakes up. Render's free database is also time-limited (about 30 days at the time of
> writing). Before an important demo or pitch, open the site yourself a minute early. For an always-on site,
> upgrade the web service and database to paid plans in Render (a few dollars a month). Check Render's pricing
> page for current details.

### Run it on your computer

You need two free programs (both have normal installers):
- **[Python](https://www.python.org/downloads/)** 3.12 or newer. On Windows, tick **Add python.exe to PATH**.
- **[Node.js](https://nodejs.org)** (the **LTS** version).

Then open a terminal (on Windows: **PowerShell**) and run:

```bash
git clone https://github.com/mbendari7/COOP-Radar.git
cd COOP-Radar
python start.py
```

(No `git`? On the GitHub page click **Code → Download ZIP**, unzip it, open a terminal in that folder, and run
`python start.py`.)

The first time takes a few minutes. It installs everything, builds the website, and creates a private database in
a `.coopradar` folder in your home folder. Then your browser opens **http://localhost:8000** by itself. Real jobs
appear on the **Jobs** page a minute or two later. After that, `python start.py` starts in a few seconds.

To stop it, press `Ctrl + C` in the terminal. To start over with empty data, delete the `.coopradar` folder in your
home folder.

---

## 2. Use it in 3 steps

### Step 1: Say what you're looking for
Click **Match my resume**. Pick the job types you want (Software & web, Data & AI, Design & UX, Business & finance
and more; each shows how many jobs are open), add a job title or keywords if you like ("data analyst"), choose a
province, work mode (on-site, hybrid, remote) and level (*Students & entry-level*, *Co-op & intern only*, or
*All levels*). Leave anything empty to see everything. Remote jobs are always included.

### Step 2: Upload your resume
Drag your resume onto the box, or click it to choose a file (PDF or Word, up to 5 MB).

You don't need an account. The site makes you a **private temporary account** that's kept for 7 days. To keep it
for good, click **Keep my account** in the yellow bar and add an email and password. Everything stays.

### Step 3: See the jobs your resume fits
**Jobs that fit your resume** lists your 20 best matches within your choices, best first, each with a score out of
100, the job's skills that are **on your resume**, and the ones **worth adding, if you have them**. Change your
choices in step 1 and click **Update my matches** any time; it's free and takes a second.

For each job:
- **View job and apply** opens the posting; apply on the company's own site. CoopRadar never applies for you.
- **Save to tracker** keeps it in your tracker.
- With an AI key: **Tailor my resume for this job**, **Write a cover letter opener**, or **Ask a question**
  ("Do I have the skills for this?"). Answers quote your resume or the posting.

The **Resume feedback** tab shows, for free, the skills employers can see on your resume and the in-demand skills
it's missing. With an AI key, **Review my resume** adds what you're good at, what to fix, how to tailor it, roles to
search for, and keywords to add (only ones that are true for you).

### Also handy
- **Jobs**: search and filter everything. The sidebar has job type, experience level, province and city, work
  mode, date posted, term and length, company, and skills. Sort by newest, deadline, company or title, and switch
  between cards and a table.
- **Tracker**: bookmark jobs, then move each one through *Applying, Applied, Interview, Offer*. You can add notes
  and dates, and export to a spreadsheet.
- **Try it with a sample resume**: opens a pre-filled sample account so you can see everything first.

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
