# Enterprise AI Ops



An enterprise-oriented AI operations service built with FastAPI, LangGraph, and PostgreSQL. It combines agent-driven workflows with policy enforcement, human approval gates, durable execution, and audit logging.



## Key capabilities



* **Agent workflows:** Plan, execute, verify, and complete tasks through a LangGraph workflow.

* **Human-in-the-loop approvals:** Gate higher-risk tool executions behind explicit approval.

* **Durable workflows:** Persist workflow checkpoints in PostgreSQL to support pausing and resuming execution.

* **Policy enforcement:** Apply authorization, permission, and risk checks before tool execution.

* **Controlled SQL access:** Validate read queries and use a dedicated read-only database role.

* **Audit trail:** Record operational events with sensitive-field redaction and append-only database protection.

* **Authentication:** Protect API operations using JWT-based authentication.

* **Testing and CI:** Run automated tests locally and through GitHub Actions.



## Technology stack



* Python

* FastAPI

* LangGraph

* PostgreSQL and SQLAlchemy

* Psycopg

* PyJWT

* Pytest

* Docker Compose



## Project structure



```text

app/

  agents/       Agent graph, state, planning, execution, verification

  audit/        Audit service

  llm/          LLM provider abstractions and implementations

  policy/       Authorization, permissions, risk, policy engine

  rag/          External project client

  tools/        Tool registry, SQL, operations, knowledge, analysis

  api.py        API routes

  main.py       Application entry point

  models.py     Database models

  workflow_runner.py

  workflow_service.py

scripts/

  init_db.py

  create_readonly_role.sql

  seed_data.py

  migrate_*.py

tests/

.github/

  workflows/

    ci.yml

docker-compose.yml

requirements.txt

.env.example

```



## Prerequisites



* Python 3.12 or a compatible Python version

* Docker Desktop with Docker Compose

* Git



## Setup



### 1. Clone the repository



```powershell

git clone https://github.com/Nikkibca/enterprise-ai-ops.git

cd enterprise-ai-ops

```



### 2. Create and activate a virtual environment



```powershell

py -3.12 -m venv .venv

.\\.venv\\Scripts\\Activate.ps1

```



If PowerShell blocks activation in the current terminal, you can allow it for that session:



```powershell

Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned

.\\.venv\\Scripts\\Activate.ps1

```



### 3. Install dependencies



```powershell

python -m pip install --upgrade pip

pip install -r requirements.txt

```



### 4. Configure environment variables



Create a local `.env` file based on the example:



```powershell

Copy-Item .env.example .env

```



Review `.env` and set the appropriate database URLs, JWT configuration, and LLM settings for your environment. Do not commit `.env` or real secrets.



The default local PostgreSQL URLs in the application use port `5433`; the CI workflow uses port `5432` for its PostgreSQL service.



### 5. Start the database services



```powershell

docker compose up -d

```



### 6. Initialize the database



```powershell

python -m scripts.init_db

```



### 7. Configure the read-only SQL role



The SQL script assumes the database contains the expected operational tables and that it is executed by a sufficiently privileged database user.



For a local PostgreSQL instance, execute it using your configured database administrator credentials. For example, if your Compose configuration uses `app_user`:



```powershell

Get-Content .\scripts\create_readonly_role.sql | docker compose exec -T postgres psql -U app_user -d enterprise_ai_ops

```



If your PostgreSQL service has a different Compose service name or does not support this invocation, run the SQL file using `psql` from your host instead.



### 8. Seed example operational data



```powershell

python -m scripts.seed_data

```



The seed script inserts example payment and payment-failure records for local development and SQL-tool tests. It deletes existing payment-failure and payment rows before inserting the sample records, so run it only against a development or test database.



## Run the API



Start the FastAPI application with:



```powershell

uvicorn app.main:app --reload

```



The service should be available at `http://127.0.0.1:8000`, subject to your local configuration.



FastAPI's interactive API documentation is typically available at `http://127.0.0.1:8000/docs`.



## Run tests



Make sure PostgreSQL is running, the schema is initialized, and the required read-only role and test data exist. Then run:



```powershell

pytest -q

```



The GitHub Actions workflow also initializes its PostgreSQL database, configures the read-only role, seeds operational data, and runs the test suite.



## Security notes



* Configure JWT secrets through environment variables; never commit production secrets.

* Keep the SQL reader account separate from the application's write-capable database account.

* Treat approval decisions and audit events as security-sensitive records.

* Use least-privilege credentials and restrict database access in deployed environments.

* Review tool permissions and risk policies before enabling execution against real systems.

* Use sample data only in development and test databases.



## Project status



The repository includes automated tests and a GitHub Actions CI workflow. Check the latest workflow run on GitHub for the current CI result.



## License



No license has been specified yet. Add a `LICENSE` file before redistributing this project under an open-source license.





