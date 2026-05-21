# Clarifications Log — FTF Agentic AI OS

> All questions asked by Prateek during the project, with answers, for future reference.
> Format: table per topic. Append new entries — never delete old ones.

---

## Database & Infrastructure

| # | Date | Question | Answer | Action / When |
|---|------|----------|--------|---------------|
| 1 | 2026-05-21 | The DB is local now. If code is pushed to Git, how does the DB work? | Git only stores `db/schema.sql` (the blueprint). PostgreSQL lives separately on whatever server you provision. Each environment (local, staging, prod) runs `schema.sql` once to create tables, then connects via `.env`. Data never goes to Git. | Nothing to do now. Revisit Sprint 10. |
| 2 | 2026-05-21 | What if I want to push to AWS later? What is the process? | Provision RDS PostgreSQL on AWS → run `schema.sql` against it → update `DATABASE_URL` in GitHub Secrets. Zero code changes. GitHub Actions cron jobs connect directly to RDS over the internet. No EC2 application server needed — GitHub Actions is the compute layer. | Sprint 10 (staging) and Sprint 11 (production). |
| 3 | 2026-05-21 | Do we need an application server on AWS? | No. Agents are Python scripts triggered by GitHub Actions cron. AWS only hosts the database (RDS). Everything else — compute, scheduling — is GitHub Actions. | Architecture locked. |

---

## Agent & Pipeline Design

| # | Date | Question | Answer | Action / When |
|---|------|----------|--------|---------------|
| — | — | — | — | — |

---

## API & Integrations

| # | Date | Question | Answer | Action / When |
|---|------|----------|--------|---------------|
| — | — | — | — | — |

---

## Business Rules

| # | Date | Question | Answer | Action / When |
|---|------|----------|--------|---------------|
| — | — | — | — | — |

---

## Security & Credentials

| # | Date | Question | Answer | Action / When |
|---|------|----------|--------|---------------|
| — | — | — | — | — |

---

## Process & Team

| # | Date | Question | Answer | Action / When |
|---|------|----------|--------|---------------|
| — | — | — | — | — |
