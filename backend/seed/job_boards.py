"""
Real employers whose public career boards CoopRadar imports from (Greenhouse, Lever, Ashby,
SmartRecruiters).

Each board's public API is meant for showing that company's jobs elsewhere; every posting
links back to the employer's own page to apply. Each had jobs in Canada, or US internships, when
added (checked 2026-10-12). Add a company by appending (company, adapter_type, board): the board
name is the last part of its careers URL, e.g. boards.greenhouse.io/<board>, jobs.lever.co/<board>,
jobs.ashbyhq.com/<board>, jobs.smartrecruiters.com/<board>. Admins can pause or re-enable any
source on the Admin page; a board that fails three runs in a row pauses itself.
"""

import asyncio
import json

from sqlalchemy import text

from app.db import AsyncSessionLocal

JOB_BOARDS: list[tuple[str, str, str]] = [
    # (company display name, adapter_type, board name)
    # --- Canadian companies and Canadian offices -------------------------------------------
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
    # --- US employers with many internships (US jobs: student roles only by default) -------
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
]


async def seed_job_boards() -> None:
    """
    Insert one ingest source per board (idempotent). A board that moved to another system
    (Hootsuite: Greenhouse to SmartRecruiters) is repointed and un-paused.
    """
    async with AsyncSessionLocal() as db:
        for company, adapter_type, board in JOB_BOARDS:
            params = {
                "name": f"{company} careers",
                "adapter_type": adapter_type,
                "config": json.dumps({"board": board, "company": company}),
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
    print(f"Seeded {len(JOB_BOARDS)} employer career boards.")


if __name__ == "__main__":
    asyncio.run(seed_job_boards())
