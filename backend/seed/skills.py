"""
The list of skills we look for, about 110 of them. Edit it right here.

Running it again updates the aliases and categories of skills already there, so edits
reach a live database on the next start. Keep aliases specific. A broad alias like
"security" or "http" would tag almost every job with the wrong skill.
"""

import asyncio

from sqlalchemy import text

from app.db import AsyncSessionLocal

SKILLS = [
    # Languages
    ("Python", ["py", "python3", "python 3"], "Language"),
    ("Java", ["java 8", "java 11", "java 17"], "Language"),
    ("C", ["c programming", "c language"], "Language"),
    ("C++", ["cpp", "c plus plus", "c/c++"], "Language"),
    ("C#", ["csharp", "c sharp", "dotnet"], "Language"),
    ("Go", ["golang", "go lang"], "Language"),
    ("Rust", ["rust lang", "rust programming"], "Language"),
    ("Swift", ["swift ios"], "Language"),
    ("Kotlin", ["kotlin android"], "Language"),
    ("TypeScript", ["ts", "typescript 5"], "Language"),
    ("JavaScript", ["js", "es6", "ecmascript", "vanilla js"], "Language"),
    ("Ruby", ["ruby on rails"], "Language"),
    ("PHP", ["php 8", "laravel"], "Language"),
    ("Scala", ["scala programming"], "Language"),
    ("R", ["r language", "rlang"], "Language"),
    ("MATLAB", ["matlab", "mathworks"], "Tool"),
    # Frontend
    ("React", ["reactjs", "react.js", "react 18"], "Framework"),
    ("Vue", ["vuejs", "vue.js", "vue 3"], "Framework"),
    ("Angular", ["angularjs", "angular 17"], "Framework"),
    ("Svelte", ["sveltekit"], "Framework"),
    ("Next.js", ["nextjs", "next js"], "Framework"),
    ("HTML", ["html5"], "Language"),
    ("CSS", ["css3", "scss", "sass", "tailwind"], "Language"),
    # Backend
    ("Node.js", ["nodejs", "node js", "express.js", "expressjs"], "Framework"),
    ("Django", ["django rest framework", "drf"], "Framework"),
    ("FastAPI", ["fastapi python"], "Framework"),
    ("Flask", ["flask python"], "Framework"),
    ("Spring", ["spring boot", "spring framework", "spring mvc"], "Framework"),
    ("ASP.NET", ["asp net", "dotnet web"], "Framework"),
    ("Ruby on Rails", ["rails", "ror"], "Framework"),
    # Databases
    ("SQL", ["structured query language"], "Tool"),
    ("PostgreSQL", ["postgres", "psql"], "Tool"),
    ("MySQL", ["mysql 8"], "Tool"),
    ("SQLite", ["sqlite3"], "Tool"),
    ("MongoDB", ["mongo", "mongodb atlas"], "Tool"),
    ("Redis", ["redis cache", "redis queue"], "Tool"),
    ("Elasticsearch", ["elastic search", "opensearch"], "Tool"),
    ("Cassandra", ["apache cassandra"], "Tool"),
    ("DynamoDB", ["dynamo db", "aws dynamodb"], "Tool"),
    # DevOps and infrastructure
    ("Docker", ["containerization", "docker compose"], "Tool"),
    ("Kubernetes", ["k8s", "kubectl", "helm"], "Tool"),
    ("Git", ["github", "gitlab", "version control"], "Tool"),
    ("Linux", ["unix", "bash", "shell scripting"], "Tool"),
    ("AWS", ["amazon web services", "ec2", "s3", "lambda"], "Cloud"),
    ("GCP", ["google cloud", "gke", "bigquery"], "Cloud"),
    ("Azure", ["microsoft azure", "aks"], "Cloud"),
    ("Terraform", ["infrastructure as code", "iac"], "Tool"),
    ("Ansible", ["configuration management"], "Tool"),
    ("Jenkins", ["jenkins pipeline"], "Tool"),
    ("GitHub Actions", ["github ci", "gha"], "Tool"),
    ("GitLab CI", ["gitlab pipeline"], "Tool"),
    # Data and ML
    ("Machine Learning", ["ml", "supervised learning"], "Domain"),
    ("Deep Learning", ["neural networks", "neural network"], "Domain"),
    ("TensorFlow", ["tf", "tensorflow 2"], "Framework"),
    ("PyTorch", ["torch", "pytorch lightning"], "Framework"),
    ("Scikit-learn", ["sklearn", "scikit learn"], "Framework"),
    ("Pandas", ["pandas dataframe"], "Tool"),
    ("NumPy", ["numpy array"], "Tool"),
    ("Spark", ["apache spark", "pyspark"], "Tool"),
    ("Kafka", ["apache kafka", "event streaming"], "Tool"),
    ("Airflow", ["apache airflow"], "Tool"),
    ("NLP", ["natural language processing", "text mining"], "Domain"),
    ("Computer Vision", ["image recognition", "object detection"], "Domain"),
    ("LLMs", ["large language models", "large language model", "llm"], "Domain"),
    # Embedded and hardware
    ("Embedded Systems", ["embedded software", "bare metal"], "Domain"),
    ("RTOS", ["real time os", "freertos", "zephyr"], "Tool"),
    ("PCB Design", ["pcb", "schematic design", "altium", "kicad"], "Domain"),
    ("Verilog", ["systemverilog", "rtl design"], "Language"),
    ("VHDL", ["fpga programming"], "Language"),
    ("FPGA", ["field programmable gate array", "xilinx", "intel fpga"], "Hardware"),
    ("Simulink", ["matlab simulink"], "Tool"),
    ("Automotive", ["automotive software", "iso 26262"], "Domain"),
    ("CAN Bus", ["can protocol", "automotive communication"], "Domain"),
    ("ROS", ["robot operating system", "ros2"], "Tool"),
    ("ARM", ["arm cortex", "arm microcontroller"], "Hardware"),
    ("STM32", ["stm32 microcontroller", "stm32cubemx"], "Hardware"),
    ("Arduino", ["arduino uno", "arduino ide"], "Hardware"),
    # Networking and security
    ("REST API", ["restful api", "http api", "openapi"], "Domain"),
    ("GraphQL", ["graphql api", "apollo graphql"], "Domain"),
    ("WebSockets", ["websocket", "real-time communication"], "Domain"),
    ("gRPC", ["grpc", "protocol buffers", "protobuf"], "Domain"),
    ("Networking", ["tcp/ip", "computer networking", "network protocols"], "Domain"),
    ("Cybersecurity", ["cyber security", "infosec", "penetration testing", "owasp"], "Domain"),
    ("Cryptography", ["encryption", "tls", "ssl"], "Domain"),
    # Project and process
    ("Agile", ["scrum", "kanban", "sprint"], "Process"),
    ("JIRA", ["jira software"], "Tool"),
    ("Confluence", ["atlassian confluence"], "Tool"),
    ("Figma", ["figjam"], "Tool"),
    # Mobile
    ("iOS", ["ios development", "swiftui", "uikit"], "Domain"),
    ("Android", ["android development", "android studio"], "Domain"),
    ("React Native", ["react-native"], "Framework"),
    ("Flutter", ["flutter mobile"], "Framework"),
    # Testing
    ("Testing", ["unit testing", "test automation", "automated testing", "pytest", "jest"], "Domain"),
    ("Selenium", ["selenium webdriver", "browser testing"], "Tool"),
    ("Jest", ["jest testing", "vitest"], "Tool"),
    ("pytest", ["pytest-asyncio", "python testing"], "Tool"),
    # Everything else
    ("Microservices", ["microservice", "service mesh"], "Domain"),
    ("System Design", ["distributed systems", "software architecture"], "Domain"),
    ("Data Structures", ["data structures and algorithms", "algorithms", "competitive programming"], "Domain"),
    ("Statistics", ["probability", "statistical analysis"], "Domain"),
    ("Excel", ["microsoft excel", "vba"], "Tool"),
    ("Power BI", ["powerbi"], "Tool"),
    ("Tableau", ["tableau desktop"], "Tool"),
    ("Solidworks", ["solid works"], "Tool"),
    ("LabVIEW", ["national instruments", "labview"], "Tool"),
    ("OpenCV", ["open cv"], "Tool"),
]


async def seed_skills() -> None:
    async with AsyncSessionLocal() as db:
        for name, aliases, category in SKILLS:
            await db.execute(
                text(
                    "INSERT INTO skills (id, name, aliases, category) "
                    "VALUES (gen_random_uuid(), :name, :aliases, :category) "
                    "ON CONFLICT (name) DO UPDATE "
                    "SET aliases = EXCLUDED.aliases, category = EXCLUDED.category"
                ),
                {"name": name, "aliases": aliases, "category": category},
            )
        await db.commit()
    print(f"Seeded {len(SKILLS)} skills.")


if __name__ == "__main__":
    asyncio.run(seed_skills())
