"""
Sample data. About 60 realistic made up co-op jobs for building and testing.

Load everything with   python -m seed          (jobs, skills and dev import sources)
Jobs only              python -c "import asyncio, seed; asyncio.run(seed.seed())"
Run both from the backend folder.

The jobs cover 8 Canadian cities plus remote, 3 co-op terms in Winter, Summer and Fall 2027,
4 lengths, and a mix of future and past deadlines so the Show expired switch has
something to show.
"""

import asyncio
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select

from app.db import AsyncSessionLocal
from app.models.posting import Posting, WorkMode

# Skills
# One fixed skill list for all the sample jobs.
# A full list lives in the skills table but a constant is fine for sample data

SKILLS_POOL = [
    "Python", "Java", "TypeScript", "JavaScript", "Go", "C++", "Rust", "Swift",
    "Kotlin", "SQL", "PostgreSQL", "MySQL", "Redis", "MongoDB",
    "React", "Vue", "Angular", "Node.js", "Django", "FastAPI", "Spring",
    "AWS", "GCP", "Azure", "Docker", "Kubernetes", "Terraform",
    "Machine Learning", "Data Analysis", "Tableau", "Figma", "Linux", ".NET",
]


# The sample jobs
# Each one is title, company, city, province, work_mode, term,
# duration, deadline, posted_at, 4 to 6 skills, description and an optional source_url

RAW: list[tuple[Any, ...]] = [
    # Toronto
    ("Backend Developer", "Shopify", "Toronto", "ON", WorkMode.hybrid,
     "Summer 2027", 4, date(2027, 2, 28), datetime(2026, 9, 10, tzinfo=UTC),
     ["Python", "Django", "PostgreSQL", "Docker"],
     "Join our core payments team. You'll build and maintain RESTful APIs serving millions of merchants. Expect real code reviews, real production deploys, and real impact.",
     "https://shopify.com/careers/123"),

    ("Data Engineer Co-op", "RBC", "Toronto", "ON", WorkMode.onsite,
     "Winter 2027", 4, date(2026, 11, 15), datetime(2026, 9, 5, tzinfo=UTC),
     ["Python", "SQL", "AWS", "Tableau"],
     "Work within the Enterprise Data team to build pipelines that power risk dashboards used by thousands of analysts across the bank.",
     None),

    ("iOS Developer", "Wealthsimple", "Toronto", "ON", WorkMode.hybrid,
     "Summer 2027", 4, date(2027, 1, 31), datetime(2026, 9, 20, tzinfo=UTC),
     ["Swift", "Kotlin", "React", "Figma"],
     "Build features for Canada's leading investing app. You'll work directly with product designers and ship to 3M+ users.",
     "https://wealthsimple.com/jobs/456"),

    ("Machine Learning Engineer", "Layer6 AI", "Toronto", "ON", WorkMode.hybrid,
     "Fall 2027", 8, date(2027, 5, 1), datetime(2026, 10, 1, tzinfo=UTC),
     ["Python", "Machine Learning", "PostgreSQL", "Docker", "AWS"],
     "Research and implement ML models for TD Bank's recommendation engine. Strong Python and linear algebra fundamentals required.",
     "https://layer6.ai/careers/789"),

    ("DevOps Engineer", "Loblaw Digital", "Toronto", "ON", WorkMode.onsite,
     "Winter 2027", 4, date(2026, 10, 31), datetime(2026, 9, 15, tzinfo=UTC),
     ["Docker", "Kubernetes", "Terraform", "AWS", "Linux"],
     "Support and scale the infrastructure running Canada's largest grocery e-commerce platform. On-call rotations included.",
     None),

    ("Full Stack Developer", "Points.com", "Toronto", "ON", WorkMode.hybrid,
     "Summer 2027", 8, date(2027, 2, 14), datetime(2026, 9, 25, tzinfo=UTC),
     ["TypeScript", "React", "Node.js", "PostgreSQL"],
     "Build and maintain features for our loyalty platform used by 50+ airline and hotel programs. TypeScript everywhere — no legacy JQuery.",
     "https://points.com/careers"),

    # Waterloo
    ("Software Engineering Intern", "Google", "Waterloo", "ON", WorkMode.hybrid,
     "Summer 2027", 4, date(2027, 1, 15), datetime(2026, 9, 3, tzinfo=UTC),
     ["C++", "Python", "Go", "SQL"],
     "Work on Google's core infrastructure or one of many product teams. Projects are assigned based on team fit and your skills.",
     "https://careers.google.com/intern"),

    ("Compiler Engineer Co-op", "AMD", "Waterloo", "ON", WorkMode.onsite,
     "Winter 2027", 8, date(2026, 11, 1), datetime(2026, 9, 8, tzinfo=UTC),
     ["C++", "Rust", "Linux", "Python"],
     "Develop and optimise LLVM-based compiler passes for GPU compute workloads. Strong CS fundamentals essential.",
     None),

    ("Backend Co-op", "Faire", "Waterloo", "ON", WorkMode.hybrid,
     "Summer 2027", 4, date(2027, 2, 1), datetime(2026, 9, 12, tzinfo=UTC),
     ["Java", "Spring", "PostgreSQL", "AWS"],
     "Build marketplace features connecting indie brands with local retailers. Real product scope — you'll own whole features.",
     "https://faire.com/jobs"),

    ("Platform Engineer", "Vidyard", "Waterloo", "ON", WorkMode.onsite,
     "Fall 2027", 4, date(2027, 4, 30), datetime(2026, 9, 22, tzinfo=UTC),
     ["Go", "Kubernetes", "Docker", "PostgreSQL"],
     "Join the platform team building the infrastructure that delivers video to 10M+ viewers. Strong Go skills expected.",
     None),

    ("Data Science Co-op", "Arctic Wolf", "Waterloo", "ON", WorkMode.hybrid,
     "Summer 2027", 8, date(2027, 2, 28), datetime(2026, 10, 2, tzinfo=UTC),
     ["Python", "Machine Learning", "SQL", "Data Analysis"],
     "Build detection models for the SOC platform. You'll work with massive security telemetry datasets.",
     "https://arcticwolf.com/careers"),

    ("Frontend Developer", "Kik Interactive", "Waterloo", "ON", WorkMode.onsite,
     "Winter 2027", 4, date(2026, 10, 20), datetime(2026, 9, 18, tzinfo=UTC),
     ["TypeScript", "React", "Node.js", "Figma"],
     "Work on the Kik messaging client. You'll write React components seen by millions of users daily.",
     None),

    # Kitchener
    ("Embedded Systems Co-op", "Dejur Inc", "Kitchener", "ON", WorkMode.onsite,
     "Summer 2027", 4, date(2027, 1, 31), datetime(2026, 9, 28, tzinfo=UTC),
     ["C++", "Rust", "Linux"],
     "Develop firmware for industrial IoT sensors. C++ required; Rust experience is a strong plus.",
     None),

    ("QA Automation Engineer", "SE Health", "Kitchener", "ON", WorkMode.hybrid,
     "Winter 2027", 4, date(2026, 11, 30), datetime(2026, 9, 14, tzinfo=UTC),
     ["Python", "SQL", "Docker"],
     "Build and maintain automated test suites for our healthcare platform. Experience with pytest or similar frameworks.",
     None),

    ("Mobile Developer Co-op", "eSentire", "Kitchener", "ON", WorkMode.hybrid,
     "Summer 2027", 4, date(2027, 2, 15), datetime(2026, 10, 3, tzinfo=UTC),
     ["Swift", "Kotlin", "React"],
     "Build features for the eSentire Atlas portal mobile app. Both iOS and Android experience welcomed.",
     "https://esentire.com/careers"),

    # Guelph
    ("Full Stack Developer", "EcoVadis", "Guelph", "ON", WorkMode.hybrid,
     "Fall 2027", 8, date(2027, 5, 15), datetime(2026, 9, 30, tzinfo=UTC),
     ["Vue", "Node.js", "PostgreSQL", "Docker"],
     "Build sustainability rating dashboards used by Fortune 500 procurement teams. Full ownership from design to deploy.",
     "https://ecovadis.com/jobs"),

    ("Data Analyst Co-op", "Co-operators", "Guelph", "ON", WorkMode.onsite,
     "Winter 2027", 4, date(2026, 11, 10), datetime(2026, 9, 6, tzinfo=UTC),
     ["SQL", "Python", "Tableau", "Data Analysis"],
     "Analyse claims data to surface underwriting insights. Tableau dashboards presented to senior leadership.",
     None),

    ("Backend Developer", "AutoTrader Canada", "Guelph", "ON", WorkMode.hybrid,
     "Summer 2027", 4, date(2027, 1, 20), datetime(2026, 9, 16, tzinfo=UTC),
     ["Java", "Spring", "MySQL", "AWS"],
     "Work on the listing search API serving 15M monthly visits. Performance matters here.",
     None),

    # Hamilton
    ("Security Analyst Co-op", "FirstOntario Credit Union", "Hamilton", "ON", WorkMode.onsite,
     "Summer 2027", 4, date(2027, 2, 1), datetime(2026, 9, 11, tzinfo=UTC),
     ["Python", "Linux", "SQL"],
     "Monitor security events, triage alerts, and contribute to incident response playbooks.",
     None),

    ("Web Developer", "McMaster University", "Hamilton", "ON", WorkMode.hybrid,
     "Winter 2027", 4, date(2026, 11, 20), datetime(2026, 9, 19, tzinfo=UTC),
     ["TypeScript", "React", "Node.js", "PostgreSQL"],
     "Build and maintain student-facing web applications for the registrar's office and library systems.",
     "https://mcmaster.ca/hr"),

    ("DevOps Co-op", "Stericycle", "Hamilton", "ON", WorkMode.onsite,
     "Fall 2027", 4, date(2027, 5, 1), datetime(2026, 9, 27, tzinfo=UTC),
     ["Docker", "Kubernetes", "Linux", "Python"],
     "Automate deployment pipelines and maintain the on-premise Kubernetes cluster running medical waste tracking systems.",
     None),

    # Ottawa
    ("Software Developer Co-op", "Kinaxis", "Ottawa", "ON", WorkMode.hybrid,
     "Summer 2027", 4, date(2027, 2, 28), datetime(2026, 9, 23, tzinfo=UTC),
     ["Java", "Spring", "PostgreSQL", "React"],
     "Build supply-chain optimisation features used by aerospace and pharma companies. Java 21 with virtual threads.",
     "https://kinaxis.com/careers"),

    ("Cloud Infrastructure Co-op", "Ciena", "Ottawa", "ON", WorkMode.onsite,
     "Winter 2027", 8, date(2026, 12, 1), datetime(2026, 9, 9, tzinfo=UTC),
     ["AWS", "Terraform", "Docker", "Python"],
     "Provision and manage cloud infrastructure for telecom network management products.",
     None),

    ("Full Stack Developer", "Telesat", "Ottawa", "ON", WorkMode.hybrid,
     "Fall 2027", 4, date(2027, 5, 30), datetime(2026, 10, 4, tzinfo=UTC),
     ["TypeScript", "React", "Node.js", "PostgreSQL"],
     "Build ground-segment control interfaces for next-generation LEO satellite systems.",
     "https://telesat.com/jobs"),

    ("Backend Co-op", "Pythian", "Ottawa", "ON", WorkMode.onsite,
     "Summer 2027", 8, date(2027, 3, 1), datetime(2026, 9, 26, tzinfo=UTC),
     ["Python", "PostgreSQL", "AWS", "Docker"],
     "Database-focused development role working alongside DBAs building managed services for enterprise clients.",
     None),

    # Mississauga
    ("Software Developer", "Huawei Canada R&D", "Mississauga", "ON", WorkMode.onsite,
     "Summer 2027", 4, date(2027, 2, 15), datetime(2026, 9, 17, tzinfo=UTC),
     ["C++", "Python", "Linux", "Go"],
     "R&D role on 5G baseband firmware. Highly technical — expect OS-level C++ and kernel debugging.",
     None),

    ("Data Engineer", "Hatch", "Mississauga", "ON", WorkMode.hybrid,
     "Winter 2027", 4, date(2026, 11, 25), datetime(2026, 9, 7, tzinfo=UTC),
     ["Python", "SQL", "AWS", "Data Analysis"],
     "Build data infrastructure for major mining and energy infrastructure projects. Real-world engineering datasets.",
     "https://hatch.com/careers"),

    ("Web Application Developer", "Amex Canada", "Mississauga", "ON", WorkMode.hybrid,
     "Fall 2027", 4, date(2027, 4, 15), datetime(2026, 9, 24, tzinfo=UTC),
     ["Java", ".NET", "React", "SQL"],
     "Work on internal tooling and customer-facing account management applications.",
     None),

    # Vancouver
    ("Software Engineer Co-op", "Hootsuite", "Vancouver", "BC", WorkMode.hybrid,
     "Summer 2027", 4, date(2027, 2, 1), datetime(2026, 9, 13, tzinfo=UTC),
     ["Scala", "React", "PostgreSQL", "AWS"],
     "Work on the social media scheduling engine processing 10M+ posts per day. Scala on the backend, React on the frontend.",
     "https://hootsuite.com/careers"),

    ("ML Platform Engineer", "Finning International", "Vancouver", "BC", WorkMode.onsite,
     "Winter 2027", 8, date(2026, 12, 15), datetime(2026, 9, 4, tzinfo=UTC),
     ["Python", "Machine Learning", "Docker", "GCP"],
     "Build MLOps infrastructure for predictive maintenance models running on mining equipment.",
     None),

    ("iOS Developer Co-op", "Slack (Salesforce)", "Vancouver", "BC", WorkMode.hybrid,
     "Summer 2027", 4, date(2027, 1, 25), datetime(2026, 9, 21, tzinfo=UTC),
     ["Swift", "Kotlin", "React", "Figma"],
     "Ship features to Slack's 20M+ daily users. Expect code review from engineers who wrote the iOS SDK.",
     "https://slack.com/intl/careers"),

    ("Backend Developer Co-op", "Hootsuite", "Vancouver", "BC", WorkMode.hybrid,
     "Fall 2027", 4, date(2027, 5, 15), datetime(2026, 10, 5, tzinfo=UTC),
     ["Go", "PostgreSQL", "Docker", "AWS"],
     "Join the platform engineering team rebuilding Hootsuite's analytics pipeline in Go.",
     None),

    ("Data Scientist", "BC Hydro", "Vancouver", "BC", WorkMode.onsite,
     "Summer 2027", 8, date(2027, 3, 15), datetime(2026, 9, 29, tzinfo=UTC),
     ["Python", "Machine Learning", "SQL", "Tableau"],
     "Model energy demand forecasting and grid stability scenarios. Work directly with operations researchers.",
     None),

    # Remote
    # Remote jobs always have to show up when filtering by city
    ("Frontend Engineer Co-op", "1Password", "Remote", "ON", WorkMode.remote,
     "Summer 2027", 4, date(2027, 2, 28), datetime(2026, 9, 16, tzinfo=UTC),
     ["TypeScript", "React", "Node.js", "Figma"],
     "Work on 1Password's web extension and browser apps. Distributed team — async-first culture, strong documentation expected.",
     "https://1password.com/jobs"),

    ("Backend Developer", "Tailscale", "Remote", "ON", WorkMode.remote,
     "Winter 2027", 4, date(2026, 11, 30), datetime(2026, 9, 10, tzinfo=UTC),
     ["Go", "Rust", "Linux", "Docker"],
     "Build features in the Tailscale daemon or control plane. Must be comfortable with networking fundamentals (WireGuard, DERP).",
     "https://tailscale.com/careers"),

    ("Data Engineer", "Properly", "Remote", "BC", WorkMode.remote,
     "Summer 2027", 4, date(2027, 1, 31), datetime(2026, 9, 20, tzinfo=UTC),
     ["Python", "SQL", "AWS", "Data Analysis"],
     "Build pipelines that power real estate pricing models. Fully remote, flexible hours, real ownership.",
     None),

    ("DevOps Co-op", "Clio", "Remote", "BC", WorkMode.remote,
     "Fall 2027", 4, date(2027, 5, 1), datetime(2026, 9, 28, tzinfo=UTC),
     ["Kubernetes", "Terraform", "Docker", "AWS"],
     "Help scale the infrastructure running Canada's #1 legal practice management platform. Remote-first, async.",
     "https://clio.com/careers"),

    ("ML Engineer", "Cohere", "Remote", "ON", WorkMode.remote,
     "Summer 2027", 8, date(2027, 3, 1), datetime(2026, 10, 1, tzinfo=UTC),
     ["Python", "Machine Learning", "Docker", "AWS"],
     "Build infrastructure for training and serving large language models. The most technically demanding co-op on this list.",
     "https://cohere.com/careers"),

    # Expired jobs with a deadline in the past
    # These stay hidden unless you turn on Show expired

    ("Software Developer (Expired)", "BlackBerry QNX", "Waterloo", "ON", WorkMode.onsite,
     "Winter 2027", 4, date(2026, 9, 30), datetime(2026, 8, 1, tzinfo=UTC),
     ["C++", "Rust", "Linux"],
     "Develop drivers for the QNX microkernel. Real-time operating system work — rare experience for a co-op.",
     None),

    ("Junior Data Analyst (Expired)", "OMERS", "Toronto", "ON", WorkMode.hybrid,
     "Winter 2027", 4, date(2026, 9, 15), datetime(2026, 8, 10, tzinfo=UTC),
     ["SQL", "Python", "Tableau", "Data Analysis"],
     "Analyse pension fund investment data. Excel-free environment — everything is Python + SQL.",
     None),

    ("Backend Co-op (Expired)", "Faire", "Waterloo", "ON", WorkMode.hybrid,
     "Winter 2027", 4, date(2026, 9, 20), datetime(2026, 8, 5, tzinfo=UTC),
     ["Java", "Spring", "PostgreSQL"],
     "Earlier intake — position has closed. Check the Summer 2027 listing above.",
     None),

    ("iOS Developer (Expired)", "Kik Interactive", "Waterloo", "ON", WorkMode.onsite,
     "Winter 2027", 4, date(2026, 10, 1), datetime(2026, 8, 15, tzinfo=UTC),
     ["Swift", "Kotlin"],
     "Deadline passed. A new intake opens for Summer 2027 shortly.",
     None),

    ("DevOps Co-op (Expired)", "Shopify", "Toronto", "ON", WorkMode.hybrid,
     "Winter 2027", 4, date(2026, 9, 25), datetime(2026, 8, 20, tzinfo=UTC),
     ["Docker", "Kubernetes", "Terraform", "AWS"],
     "Previous intake — closed. Multiple DevOps roles opening in Summer 2027.",
     None),

    # A few more Summer 2027 jobs to get to about 60
    ("Cloud Engineer", "Sun Life Financial", "Toronto", "ON", WorkMode.hybrid,
     "Summer 2027", 8, date(2027, 2, 10), datetime(2026, 9, 22, tzinfo=UTC),
     ["AWS", "Terraform", "Python", "Docker"],
     "Automate infrastructure provisioning for Sun Life's hybrid cloud. Python CDK preferred.",
     None),

    ("Backend Developer", "FreshBooks", "Toronto", "ON", WorkMode.hybrid,
     "Summer 2027", 4, date(2027, 2, 20), datetime(2026, 9, 24, tzinfo=UTC),
     ["Python", "Django", "PostgreSQL", "React"],
     "Build accounting features for 30M users. Django 5 REST API, React frontend, strong code review culture.",
     "https://freshbooks.com/careers"),

    ("Platform Co-op", "Descartes Systems", "Waterloo", "ON", WorkMode.onsite,
     "Summer 2027", 4, date(2027, 1, 10), datetime(2026, 9, 15, tzinfo=UTC),
     ["Java", "Spring", "SQL", "AWS"],
     "Work on the Global Logistics Network platform processing 1B+ transactions/year.",
     None),

    ("Software Engineering Co-op", "Miovision", "Kitchener", "ON", WorkMode.hybrid,
     "Summer 2027", 4, date(2027, 2, 5), datetime(2026, 9, 26, tzinfo=UTC),
     ["Python", "Go", "PostgreSQL", "Docker"],
     "Process real-time traffic sensor data from 30,000+ intersections. Python or Go preferred.",
     "https://miovision.com/careers"),

    ("Frontend Developer", "Brock Solutions", "Kitchener", "ON", WorkMode.onsite,
     "Fall 2027", 4, date(2027, 5, 20), datetime(2026, 10, 3, tzinfo=UTC),
     ["TypeScript", "React", "Node.js"],
     "Build real-time operational dashboards for airport baggage handling systems.",
     None),

    ("Data Analyst", "Linamar", "Guelph", "ON", WorkMode.onsite,
     "Summer 2027", 4, date(2027, 1, 25), datetime(2026, 9, 18, tzinfo=UTC),
     ["SQL", "Python", "Tableau"],
     "Analyse manufacturing process data from 60+ facilities. Strong SQL required.",
     None),

    ("iOS/Android Co-op", "Intellicheck", "Hamilton", "ON", WorkMode.hybrid,
     "Summer 2027", 4, date(2027, 2, 28), datetime(2026, 9, 29, tzinfo=UTC),
     ["Swift", "Kotlin", "React"],
     "Build mobile ID verification features for security-critical use cases.",
     None),

    ("Platform Security Co-op", "Assent", "Ottawa", "ON", WorkMode.hybrid,
     "Summer 2027", 4, date(2027, 2, 15), datetime(2026, 9, 20, tzinfo=UTC),
     ["Python", "Linux", "Docker", "SQL"],
     "Security tooling and vulnerability management for the supply chain compliance platform.",
     "https://assent.com/careers"),

    ("Full Stack Co-op", "Bit Space Development", "Ottawa", "ON", WorkMode.onsite,
     "Fall 2027", 8, date(2027, 6, 1), datetime(2026, 10, 5, tzinfo=UTC),
     ["TypeScript", "React", "Node.js", "PostgreSQL"],
     "Small team, big scope. Build and deploy full features for government and NGO clients.",
     None),

    ("Cloud Infrastructure", "Rogers Communications", "Mississauga", "ON", WorkMode.hybrid,
     "Summer 2027", 8, date(2027, 3, 10), datetime(2026, 9, 27, tzinfo=UTC),
     ["AWS", "Terraform", "Kubernetes", "Python"],
     "Migrate workloads to AWS and improve CI/CD pipelines for Canada's largest telecom.",
     None),

    ("Backend Developer", "Best Buy Canada", "Vancouver", "BC", WorkMode.hybrid,
     "Summer 2027", 4, date(2027, 1, 30), datetime(2026, 9, 14, tzinfo=UTC),
     ["Java", "Spring", "PostgreSQL", "AWS"],
     "Build and scale APIs for the e-commerce platform handling peak Black Friday traffic.",
     "https://careers.bestbuy.ca"),

    ("Data Engineer Co-op", "Absolute Security", "Vancouver", "BC", WorkMode.hybrid,
     "Fall 2027", 4, date(2027, 5, 15), datetime(2026, 10, 4, tzinfo=UTC),
     ["Python", "SQL", "AWS", "Data Analysis"],
     "Build data pipelines for endpoint security telemetry at global scale.",
     None),
]


async def seed() -> None:
    """
    Add the sample jobs. Safe to rerun. Jobs that are already there with the same title,
    company and city get skipped so running it again never deletes anyone's saved jobs.
    """
    async with AsyncSessionLocal() as session:
        existing = {
            (t, c, city)
            for t, c, city in (
                await session.execute(select(Posting.title, Posting.company, Posting.city))
            ).all()
        }

        added = 0
        for (
            title, company, city, province, work_mode, term,
            duration, deadline, posted_at, skills, description, source_url,
        ) in RAW:
            if (title, company, city) in existing:
                continue
            session.add(
                Posting(
                    title=title,
                    company=company,
                    city=city,
                    province=province,
                    work_mode=work_mode,
                    term=term,
                    duration_months=duration,
                    deadline=deadline,
                    posted_at=posted_at,
                    skills=skills,
                    description=description,
                    source_url=source_url,
                )
            )
            added += 1

        await session.commit()

    print(f"Seeded {added} postings ({len(RAW) - added} already present).")


if __name__ == "__main__":
    asyncio.run(seed())
