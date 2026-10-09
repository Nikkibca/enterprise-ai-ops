# Enterprise AI Operations Platform

An AI-powered operations platform built with **FastAPI, LangGraph, and PostgreSQL** that demonstrates how enterprise AI agents can execute tasks under controlled permissions, human approval gates, and auditable workflows.

The platform combines agent orchestration with security-focused execution controls to help make AI-driven operational workflows more manageable, traceable, and reliable.

## Key capabilitiesPS C:\Users\nikki\enterprise-ai-ops> (Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned) ; (& c:\Users\nikki\enterprise-ai-ops\.venv\Scripts\Activate.ps1)
(.venv) PS C:\Users\nikki\enterprise-ai-ops> Get-Content README.md -TotalCount 35
# Enterprise AI Operations Platform

An AI-powered operations platform built with **FastAPI, LangGraph, and PostgreSQL** that demonstrates how enterprise AI agents can execute tasks under controlled permissions, human approval gates, and auditable workflows.

The platform combines agent orchestration with security-focused execution controls to help make AI-driven operational workflows more manageable, traceable, and reliable.

## Key capabilities

* **AI agent orchestration:** Plan, execute, verify, and complete tasks through a LangGraph workflow.
* **Human-in-the-loop approvals:** Require approval before executing higher-risk operations.
* **Durable workflow execution:** Persist workflow checkpoints in PostgreSQL to support pausing and resuming execution.
* **Policy-based authorization:** Evaluate user permissions and tool risk before execution.
* **Read-only SQL access:** Validate read queries and use a dedicated database role with restricted privileges.
* **Auditable operations:** Record operational events with sensitive-field redaction and database protections.
* **JWT authentication:** Protect API operations using token-based authentication.
* **Automated quality checks:** Run the test suite locally and through GitHub Actions CI.

This project demonstrates secure AI application engineering, workflow orchestration, and enterprise-oriented backend design.

## Technology stack

* Python 3.12
* FastAPI
* LangGraph
* PostgreSQL
* SQLAlchemy
* Psycopg
* PyJWT
* Pytest
* Docker Compose
* GitHub Actions

## Project architecture

The application uses a workflow-oriented architecture in which an AI agent coordinates tasks and invokes registered tools. A policy engine evaluates permissions and risk, while approval gates help control higher-risk operations. PostgreSQL supports application data, audit records, and durable workflow checkpoints.
(.venv) PS C:\Users\nikki\enterprise-ai-ops> Get-Content README.md -Tail 25
* **SQL validation:** Validate read queries and maintain database-level read-only restrictions as defense in depth.
* **Human approval:** Require approval for high-risk operations according to the configured policy.
* **Auditability:** Treat audit records and approval decisions as security-sensitive data.
* **Secrets management:** Never commit `.env` files, passwords, API keys, or production credentials.
* **Database safety:** Use sample data only in development and test environments.
* **Deployment hardening:** Configure appropriate network restrictions, HTTPS, secret management, database permissions, and operational monitoring before exposing the service publicly.

This repository is a development and portfolio project. Review its authentication, authorization, infrastructure, and operational controls before using it in a production environment.

## Project status

The project includes an agent workflow, policy-based tool execution, approval controls for higher-risk actions, PostgreSQL-backed persistence, JWT authentication, audit logging, and automated tests.

The current verified development milestone includes:

* Application startup and health endpoint verified.
* Interactive API documentation verified.
* 260 local automated tests passing.
* GitHub Actions CI passing for commit `d7d22ab`.

These results describe the verified state at the time of writing; consult the repository and latest CI run for subsequent changes.

## License

No license has been specified yet. Add an appropriate `LICENSE` file before distributing this repository under an open-source license. Without a license, others generally do not receive permission to reuse, modify, or redistribute the code beyond applicable legal exceptions.

* **AI agent orchestration:** Plan, execute, verify, and complete tasks through a LangGraph workflow.
* **Human-in-the-loop approvals:** Require approval before executing higher-risk operations.
* **Durable workflow execution:** Persist workflow checkpoints in PostgreSQL to support pausing and resuming execution.
* **Policy-based authorization:** Evaluate user permissions and tool risk before execution.
* **Read-only SQL access:** Validate read queries and use a dedicated database role with restricted privileges.
* **Auditable operations:** Record operational events with sensitive-field redaction and database protections.
* **JWT authentication:** Protect API operations using token-based authentication.
* **Automated quality checks:** Run the test suite locally and through GitHub Actions CI.

This project demonstrates secure AI application engineering, workflow orchestration, and enterprise-oriented backend design.

## Technology stack

* Python 3.12
* FastAPI
* LangGraph
* PostgreSQL
* SQLAlchemy
* Psycopg
* PyJWT
* Pytest
* Docker Compose
* GitHub Actions

## Project architecture

The application uses a workflow-oriented architecture in which an AI agent coordinates tasks and invokes registered tools. A policy engine evaluates permissions and risk, while approval gates help control higher-risk operations. PostgreSQL supports application data, audit records, and durable workflow checkpoints.

```text
Client
  |
  v
FastAPI Application
  |
  v
Authentication (JWT)
  |
  v
Workflow Service
  |
  v
LangGraph Agent Workflow
  |
  +---- Planning
  |
  +---- Policy and Permission Checks
  |
  +---- Tool Execution
  |       |
  |       +---- Knowledge Search
  |       +---- Read-only SQL
  |       +---- Python Analysis
  |       +---- Service Restart
  |
  +---- Human Approval for High-Risk Actions
  |
  +---- Verification and Completion
  |
  v
Audit Logging and PostgreSQL Checkpoints
```

## Project structure

```text
enterprise-ai-ops/
├── app/
│   ├── agents/          # Agent graph, state, planning, execution, verification
│   ├── audit/           # Audit logging services
│   ├── llm/             # LLM provider settings and implementations
│   ├── policy/          # Authorization, permissions, risk, policy engine
│   ├── rag/             # External project client
│   ├── tools/           # Tool registry and tool implementations
│   ├── api.py           # API routes
│   ├── main.py          # FastAPI application entry point
│   ├── models.py        # Database models
│   ├── workflow_runner.py
│   └── workflow_service.py
├── scripts/
│   ├── init_db.py
│   ├── create_readonly_role.sql
│   ├── seed_data.py
│   └── migrate_*.py
├── tests/
├── .github/
│   └── workflows/
│       └── ci.yml
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

## Prerequisites

* Python 3.12 or a compatible Python version
* Docker Desktop with Docker Compose
* Git

## Setup and installation

### 1. Clone the repository

```powershell
git clone https://github.com/Nikkibca/enterprise-ai-ops.git
cd enterprise-ai-ops
```

### 2. Create and activate a virtual environment

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation in the current terminal, allow it for that session:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. Configure environment variables

Create a local `.env` file from the example:

```powershell
Copy-Item .env.example .env
```

Review `.env` and configure the appropriate database URLs, JWT settings, and LLM settings for your environment.

**Never commit `.env` files, production credentials, API keys, or real secrets to GitHub.**

The default local PostgreSQL URLs use port `5433`. The GitHub Actions workflow configures its PostgreSQL service on port `5432`.

Ensure required environment variables are configured before starting the application or running database-dependent tests. Use strong, unique secrets and deployment-specific credentials outside local development.

### 5. Start PostgreSQL

```powershell
docker compose up -d
```

Check the database service status:

```powershell
docker compose ps
```

### 6. Initialize the database

```powershell
python -m scripts.init_db
```

### 7. Configure the read-only SQL role

The SQL setup script expects the required operational tables to exist and must be executed by a database user with sufficient privileges.

For the local Docker Compose setup, run:

```powershell
Get-Content .\scripts\create_readonly_role.sql | docker compose exec -T postgres psql -U app_user -d enterprise_ai_ops
```

Verify that the read-only account has only the intended access. Review and adapt the SQL setup when using a different database environment or deployment configuration.

### 8. Seed example operational data

```powershell
python -m scripts.seed_data
```

The seed script inserts sample payment and payment-failure records for local development and testing. It deletes existing payment and payment-failure rows before inserting sample data.

**Run the seed script only against a development or test database. Never run it against production data.**

## Run the application

Start the FastAPI application:

```powershell
python -m uvicorn app.main:app --reload
```

The application should be available at:

* **API base URL:** http://127.0.0.1:8000
* **Interactive API documentation:** http://127.0.0.1:8000/docs
* **Health endpoint:** http://127.0.0.1:8000/health

The application requires its configured dependencies, including PostgreSQL and workflow checkpoint storage, to initialize successfully.

## Run tests

Ensure PostgreSQL is running, the database schema is initialized, the read-only SQL role is configured, and the required test data and environment variables are available.

Run the complete test suite:

```powershell
python -m pytest -q
```

The project has passed **260 automated tests** in the current verified local run. Test results may change as the code evolves.

GitHub Actions CI also initializes its PostgreSQL test database, configures the read-only role, seeds sample data, and runs automated checks.

Check the repository's Actions page for the latest CI result:

https://github.com/Nikkibca/enterprise-ai-ops/actions

## Security considerations

* **Authentication:** Configure JWT signing secrets through environment variables. Use strong, unique secrets in deployed environments.
* **Least privilege:** Keep the SQL reader account separate from the application's write-capable database account.
* **SQL validation:** Validate read queries and maintain database-level read-only restrictions as defense in depth.
* **Human approval:** Require approval for high-risk operations according to the configured policy.
* **Auditability:** Treat audit records and approval decisions as security-sensitive data.
* **Secrets management:** Never commit `.env` files, passwords, API keys, or production credentials.
* **Database safety:** Use sample data only in development and test environments.
* **Deployment hardening:** Configure appropriate network restrictions, HTTPS, secret management, database permissions, and operational monitoring before exposing the service publicly.

This repository is a development and portfolio project. Review its authentication, authorization, infrastructure, and operational controls before using it in a production environment.

## Project status

The project includes an agent workflow, policy-based tool execution, approval controls for higher-risk actions, PostgreSQL-backed persistence, JWT authentication, audit logging, and automated tests.

The current verified development milestone includes:

* Application startup and health endpoint verified.
* Interactive API documentation verified.
* 260 local automated tests passing.
* GitHub Actions CI passing for commit `d7d22ab`.

These results describe the verified state at the time of writing; consult the repository and latest CI run for subsequent changes.

## License

No license has been specified yet. Add an appropriate `LICENSE` file before distributing this repository under an open-source license. Without a license, others generally do not receive permission to reuse, modify, or redistribute the code beyond applicable legal exceptions.
