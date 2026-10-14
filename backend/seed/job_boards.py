"""
Real employers whose public career boards CoopRadar imports from. They use Greenhouse,
Lever, Ashby, SmartRecruiters or Workday. Workday is what most big employers outside tech
use, so it brings banks, insurers, energy, health care, pharma, aerospace, food, retail,
accounting and universities.

Each board's public API is made for showing that company's jobs on other sites, and every
job links back to the employer's own page to apply. Each one had jobs in Canada or US
internships when we added it on 2026-10-12. To add a company, add a line with the company,
adapter_type and board. The board is the last part of the careers URL, like
boards.greenhouse.io/<board>, jobs.lever.co/<board>, jobs.ashbyhq.com/<board> or
jobs.smartrecruiters.com/<board>. For Workday the board is "<tenant>.<wdN>/<site>" from
<tenant>.<wdN>.myworkdayjobs.com/<site>, and an optional fourth item adds settings like a
home city (see app/ingest/workday.py). The Workday ones were checked on 2026-10-13. Admins can pause or turn on any source on the Admin page,
and a board that fails three runs in a row pauses itself.
"""

import asyncio
import json
from pathlib import Path

from sqlalchemy import text

from app.db import AsyncSessionLocal

JOB_BOARDS: list[tuple[str, str, str] | tuple[str, str, str, dict[str, str]]] = [
    # Company name we show, adapter_type, board name
    # Canadian companies and Canadian offices
    ("Stripe", "greenhouse", "stripe"),
    ("Robinhood", "greenhouse", "robinhood"),
    ("Databricks", "greenhouse", "databricks"),
    ("Instacart", "greenhouse", "instacart"),
    ("Samsara", "greenhouse", "samsara"),
    ("Affirm", "greenhouse", "affirm"),
    ("Asana", "greenhouse", "asana"),
    ("Faire", "greenhouse", "faire"),
    ("Geotab", "greenhouse", "geotab"),
    ("Geotab Early Talent", "greenhouse", "internshiplist2000"),  # Geotab's co-op board
    ("D2L", "greenhouse", "d2l"),
    ("Hootsuite", "smartrecruiters", "hootsuite"),
    ("Lyft", "greenhouse", "lyft"),
    ("Pinterest", "greenhouse", "pinterest"),
    ("Okta", "greenhouse", "okta"),
    ("Reddit", "greenhouse", "reddit"),
    ("Flipp", "greenhouse", "flipp"),
    ("Wattpad", "lever", "wattpad"),
    ("Float", "ashby", "float"),
    ("Cohere", "ashby", "cohere"),
    ("Wealthsimple", "ashby", "wealthsimple"),
    ("1Password", "ashby", "1password"),
    ("Lightspeed", "ashby", "lightspeedhq"),
    ("Jobber", "ashby", "jobber"),
    ("Miovision", "ashby", "miovision"),
    ("Benevity", "ashby", "benevity"),
    ("Trulioo", "ashby", "trulioo"),
    ("Thinkific", "ashby", "thinkific"),
    ("Equitable Bank", "lever", "eqbank"),
    ("Clutch", "greenhouse", "clutch"),
    ("GitLab", "greenhouse", "gitlab"),
    ("General Dynamics Mission Systems Canada", "smartrecruiters", "gdmsi"),
    ("Neo Financial", "ashby", "neofinancial"),
    ("Elk Valley Resources", "lever", "evr"),
    ("AppDirect", "greenhouse", "appdirect"),
    ("Felix Health", "ashby", "felix"),
    ("Tenstorrent", "greenhouse", "tenstorrent"),
    ("Tenstorrent University", "greenhouse", "tenstorrentuniversity"),
    ("StackAdapt", "greenhouse", "stackadapt"),
    ("Waabi", "lever", "waabi"),
    ("Ubisoft", "smartrecruiters", "Ubisoft2"),
    ("DoorDash Canada", "greenhouse", "doordashcanada"),
    ("Brex", "greenhouse", "brex"),
    ("Elastic", "greenhouse", "elastic"),
    ("Tailscale", "greenhouse", "tailscale"),
    ("Beacon Software", "ashby", "beaconsoftware"),
    ("Moment Energy", "greenhouse", "momentenergy"),
    ("Epic Games", "greenhouse", "epicgames"),
    ("Later", "greenhouse", "later"),
    ("MongoDB", "greenhouse", "mongodb"),
    ("Zip", "ashby", "zip"),
    ("Ramp", "ashby", "ramp"),
    ("PointClickCare", "lever", "pointclickcare"),
    ("Toast", "greenhouse", "toast"),
    ("Solink", "ashby", "solink"),
    ("Mozilla", "greenhouse", "mozilla"),
    ("Kepler Communications", "lever", "kepler"),
    ("TELUS Digital", "ashby", "telus-digital"),
    ("Magnet Forensics", "lever", "magnetforensics"),
    ("Nuclear Promise X", "ashby", "NPX"),
    ("ShyftLabs", "lever", "shyftlabs"),
    ("Sony Interactive Entertainment", "greenhouse", "sonyinteractiveentertainmentglobal"),
    ("Cresta", "greenhouse", "cresta"),
    ("Lightmatter", "greenhouse", "lightmatter"),
    ("Block", "greenhouse", "block"),
    ("Sierra", "ashby", "Sierra"),
    ("Maple", "lever", "getmaple"),
    ("Loopio", "ashby", "loopio"),
    ("Bree", "ashby", "bree"),
    ("DRW", "greenhouse", "drweng"),
    ("Arista Networks", "smartrecruiters", "aristanetworks"),
    ("Achievers", "lever", "achievers"),
    ("Airbnb", "greenhouse", "airbnb"),
    ("Procurify", "ashby", "procurify"),
    ("Human Computer Lab", "ashby", "human-computer-lab"),
    ("Mirego", "lever", "mirego"),
    ("Twilio", "greenhouse", "twilio"),
    ("Fullscript", "lever", "fullscript"),
    ("Kabam", "lever", "kabam"),
    ("Keenfinity", "smartrecruiters", "keenfinity"),
    ("Coinbase", "greenhouse", "coinbase"),
    ("Dropbox", "greenhouse", "dropbox"),
    ("Klue", "ashby", "klue"),
    ("Shakepay", "greenhouse", "shakepay"),
    ("Carta", "greenhouse", "carta"),
    ("Acceldata", "lever", "acceldata"),
    ("PagerDuty", "greenhouse", "pagerduty"),
    ("PolicyMe", "lever", "policyme"),
    ("Snowflake", "ashby", "snowflake"),
    ("Vanta", "ashby", "vanta"),
    ("GoMaterials", "lever", "gomaterials"),
    ("Fivetran", "greenhouse", "fivetran"),
    ("Wave", "lever", "waveapps"),
    ("Assent", "smartrecruiters", "assent"),
    ("Khan Academy", "greenhouse", "khanacademy"),
    ("Hopper", "ashby", "hopper"),
    ("TribalScale", "greenhouse", "tribalscale"),
    ("Verkada", "greenhouse", "verkada"),
    ("Apera AI", "greenhouse", "aperaaiinc"),
    ("Workleap", "greenhouse", "workleap"),
    ("Ada", "greenhouse", "ada18"),
    ("Clearco", "ashby", "clearco"),
    ("AbCellera", "greenhouse", "abcellera"),
    ("Spare", "ashby", "spare"),
    # US employers with lots of internships. By default we only keep their student roles
    ("Palantir", "lever", "palantir"),
    ("Rocket Lab", "greenhouse", "rocketlab"),
    ("Astera Labs", "greenhouse", "asteraearlycareer2027"),
    ("Waymo", "greenhouse", "waymo"),
    ("Zoox", "lever", "zoox"),
    ("Klaviyo", "greenhouse", "klaviyocampus"),
    ("Figma", "greenhouse", "figma"),
    ("Hermeus", "lever", "hermeus"),
    ("Base Power", "ashby", "base-power"),
    ("Tanium", "greenhouse", "tanium"),
    ("Figure", "greenhouse", "figureai"),
    ("Saronic", "ashby", "saronic"),
    ("Veeam Software", "greenhouse", "veeamsoftware"),
    ("QuEra Computing", "greenhouse", "queracomputinginc"),
    ("Helion Energy", "ashby", "helion"),
    ("Kodiak Robotics", "greenhouse", "kodiak"),
    ("Roblox", "greenhouse", "roblox"),
    ("Scale AI", "greenhouse", "scaleai"),
    # Workday career sites. Sites with up to 300 jobs keep every Canadian job, bigger ones
    # keep student and campus roles (see app/ingest/workday.py)
    # Banking, insurance and investing
    ("TD", "workday", "td.wd3/TD_Bank_Careers"),
    ("RBC", "workday", "rbc.wd3/RBCGLOBAL1"),
    ("BMO", "workday", "bmo.wd3/External"),
    ("CIBC", "workday", "cibc.wd3/search"),
    ("Desjardins", "workday", "desjardins.wd10/desjardins"),
    ("Manulife", "workday", "manulife.wd3/MFCJH_Jobs"),
    ("Sun Life", "workday", "sunlife.wd3/Experienced-Jobs"),
    ("Sun Life Campus", "workday", "sunlife.wd3/Campus"),
    ("Aviva Canada", "workday", "aviva.wd1/External"),
    ("Travelers", "workday", "travelers.wd5/External"),
    ("Athene", "workday", "athene.wd5/athene_Careers"),
    ("PSP Investments", "workday", "investpsp.wd3/psp_careers"),
    ("Brookfield", "workday", "brookfield.wd5/Brookfield"),
    ("S&P Global", "workday", "spgi.wd5/spgi_Careers"),
    # Accounting and consulting
    ("BDO Canada", "workday", "bdo.wd3/bdo"),
    ("PwC", "workday", "pwc.wd3/Global_Experienced_Careers"),
    ("Thomson Reuters", "workday", "thomsonreuters.wd5/External_Career_Site"),
    ("Parsons", "workday", "parsons.wd5/Search"),
    # Energy, utilities and mining
    ("Enbridge", "workday", "enbridge.wd3/enbridge_careers"),
    ("TC Energy", "workday", "tcenergy.wd3/CAREER_SITE_TC"),
    ("Cenovus", "workday", "cenovus.wd3/careers"),
    ("Suncor", "workday", "suncor.wd1/Suncor_External"),
    ("Capital Power", "workday", "capitalpower.wd10/External"),
    ("Rio Tinto", "workday", "riotinto.wd3/RioTinto_Careers"),
    # Manufacturing, aerospace and automotive
    ("CAE", "workday", "cae.wd3/career"),
    ("Magna", "workday", "magna.wd3/Magna"),
    ("IKO", "workday", "iko.wd3/iko_Careers"),
    ("Boeing", "workday", "boeing.wd1/EXTERNAL_CAREERS"),
    ("3M", "workday", "3m.wd1/Search"),
    # Food and retail
    ("Agropur", "workday", "agropur.wd3/agropur_Careers"),
    ("Gap Inc.", "workday", "gapinc.wd1/gapinc"),
    ("The Home Depot", "workday", "homedepot.wd5/CareerDepot"),
    # Health care, pharma and medical devices
    ("McKesson", "workday", "mckesson.wd3/External_Careers"),
    ("Pfizer", "workday", "pfizer.wd1/PfizerCareers"),
    ("AstraZeneca", "workday", "astrazeneca.wd3/Careers"),
    ("GSK", "workday", "gsk.wd5/GSKCareers"),
    ("Johnson & Johnson", "workday", "jj.wd5/JJ"),
    ("Medtronic", "workday", "medtronic.wd1/MedtronicCareers"),
    ("Stryker", "workday", "stryker.wd1/StrykerCareers"),
    ("Amgen", "workday", "amgen.wd1/Careers"),
    ("Abbott", "workday", "abbott.wd5/abbottCareers"),
    # Universities
    ("McGill University", "workday", "mcgill.wd3/mcgill_careers",
     {"city": "Montréal", "province": "QC"}),
    ("UBC", "workday", "ubc.wd10/ubcstaffjobs", {"city": "Vancouver", "province": "BC"}),
    # Tech and telecom on Workday
    ("Ciena", "workday", "ciena.wd5/Careers"),
    ("Lumentum", "workday", "lumentum.wd5/LITE"),
    ("Autodesk", "workday", "autodesk.wd1/Ext"),
    ("Intel", "workday", "intel.wd1/External"),
    ("HP", "workday", "hp.wd5/ExternalCareerSite"),
    ("Cisco", "workday", "cisco.wd5/Cisco_Careers"),
    ("Adobe", "workday", "adobe.wd5/external_experienced"),
    ("Salesforce", "workday", "salesforce.wd12/External_Career_Site"),
    ("NVIDIA", "workday", "nvidia.wd5/NVIDIAExternalCareerSite"),
]

# Workable's public job search. Thousands of small employers in every field post there
WORKABLE_SOURCES: list[tuple[str, dict[str, str]]] = [
    ("Workable jobs (Canada)", {"location": "Canada"}),
    ("Workable student jobs (US)", {
        "location": "United States", "queries": "intern|co-op|student|new grad", "pages": "60",
    }),
]

_DISCOVERED = Path(__file__).with_name("discovered_boards.json")


def discovered_boards() -> list[dict[str, str]]:
    """
    Boards seed/discover_boards.py found in Common Crawl that had jobs in Canada or US student
    roles. An empty list when the file is missing or broken.
    """
    try:
        rows = json.loads(_DISCOVERED.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    adapters = {"greenhouse", "lever", "ashby", "workday", "smartrecruiters"}
    return [
        {"company": str(r["company"]), "adapter_type": str(r["adapter_type"]), "board": str(r["board"])}
        for r in rows
        if isinstance(r, dict) and r.get("adapter_type") in adapters and r.get("board") and r.get("company")
    ]


# Adzuna gathers jobs from employer sites in every field. Only added when its keys are set
ADZUNA_SOURCES: list[tuple[str, dict[str, str]]] = [
    ("Adzuna student jobs (Canada)", {"country": "ca"}),
    ("Adzuna internships (US)", {"country": "us", "what_or": "intern internship co-op", "pages": "4"}),
]


async def seed_job_boards() -> None:
    """
    Add one import source per board, safe to rerun. A board that moved to another system,
    like Hootsuite going from Greenhouse to SmartRecruiters, gets pointed at the new one and unpaused.
    """
    from app.ingest.adzuna import adzuna_configured

    entries: list[tuple[str, str, dict[str, str]]] = []
    for company, adapter_type, board, *extra in JOB_BOARDS:
        config = {"board": board, "company": company, **(extra[0] if extra else {})}
        entries.append((f"{company} careers", adapter_type, config))
    taken = {name for name, _, _ in entries}
    for row in discovered_boards():
        name = f"{row['company']} careers"
        if name in taken:
            name = f"{row['company']} careers ({row['board']})"
        taken.add(name)
        entries.append((name, row["adapter_type"], {"board": row["board"], "company": row["company"]}))
    entries += [(name, "workable", config) for name, config in WORKABLE_SOURCES]
    if adzuna_configured():
        entries += [(name, "adzuna", config) for name, config in ADZUNA_SOURCES]

    async with AsyncSessionLocal() as db:
        for name, adapter_type, config in entries:
            params = {
                "name": name,
                "adapter_type": adapter_type,
                "config": json.dumps(config),
            }
            await db.execute(
                text(
                    "INSERT INTO ingest_sources (id, name, adapter_type, config) "
                    "SELECT gen_random_uuid(), :name, :adapter_type, CAST(:config AS jsonb) "
                    "WHERE NOT EXISTS (SELECT 1 FROM ingest_sources WHERE name = :name)"
                ),
                params,
            )
            await db.execute(
                text(
                    "UPDATE ingest_sources SET adapter_type = :adapter_type, "
                    "config = CAST(:config AS jsonb), auto_paused = false, consecutive_failures = 0 "
                    "WHERE name = :name AND adapter_type <> :adapter_type"
                ),
                params,
            )
        await db.commit()
    print(f"Seeded {len(entries)} employer career boards and job feeds.")


if __name__ == "__main__":
    asyncio.run(seed_job_boards())
