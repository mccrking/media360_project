Automation options for periodic ingestion

1) Quick (run locally)

Run the loop script in the Streamlit container or any container that has the project mounted and Python deps installed:

```bash
# from project root (Windows PowerShell)
docker compose exec -T streamlit bash -lc "INTERVAL_SECONDS=300 python /opt/project/scripts/run_batch_insert.py"
# or run the loop
docker compose exec -T streamlit bash -lc "INTERVAL_SECONDS=300 /opt/project/scripts/ingest_loop.sh &"
```

2) As a Docker service (recommended for production)

Add this service to your docker-compose.yml (example):

```yaml
  ingest:
    image: python:3.11-slim
    volumes:
      - ./:/opt/project:ro
    working_dir: /opt/project
    command: ["/bin/bash", "-c", "pip install -r requirements.txt && INTERVAL_SECONDS=300 /opt/project/scripts/ingest_loop.sh"]
    depends_on:
      - postgres
```

3) Windows Task Scheduler

Create a scheduled task that runs `python scripts/run_batch_insert.py` every X minutes.

Notes:
- Ensure the environment used has the same Python deps as the container (feedparser, requests, bs4, dateutil, psycopg2).
- For production, prefer running ingestion in a small worker container with proper logging and restart policy.
