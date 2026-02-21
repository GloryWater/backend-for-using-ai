Act as an expert Developer Relations (DevRel) Engineer and Lead Open-Source Maintainer. 
Your task is to generate a complete, production-ready Open Source Documentation Suite for my project. 

### Project Context
- **Name:** FastAPI URL Shortener v3.0
- **Description:** A high-load, distributed URL shortener service.
- **Tech Stack:** Python 3.12, FastAPI, PostgreSQL (asyncpg), Redis (caching & rate limiting), background workers (queue), Docker, GitHub Actions.
- **Key Features:** High-speed cached redirects, background analytics enrichment (GeoIP, User-Agent), user authentication (JWT), automatic expiration cleanup, and a Glassmorphism Vanilla JS frontend.

### Task Requirements
Generate the following files in accordance with 2026 Open Source best practices (OSPO standards). 
Because we are communicating via CLI, you MUST wrap the content of EACH file in a Markdown code block. The very first line inside the code block must be a comment with the exact file path (e.g., `<!-- filepath: README.md -->`).

Please generate the following files sequentially:

1. **`README.md`** 
   - Must include: Project logo/header placeholder, modern shields/badges (build, coverage, license, python version), visually appealing Table of Contents.
   - Sections: Features, Architecture Diagram (text description or mermaid.js), Quickstart (Docker & Local), Environment Variables, API Endpoints summary, and License.
   
2. **`CONTRIBUTING.md`**
   - Must explain: How to set up the dev environment (`uv sync`, pre-commit hooks, docker-compose), Git Flow (branch naming conventions), and testing requirements (`pytest-asyncio`).

3. **`SECURITY.md`**
   - Must include: Supported versions table and a clear, responsible disclosure policy for reporting security vulnerabilities (e.g., email or GitHub Private Vulnerability Reporting).

4. **`CHANGELOG.md`**
   - Use the "Keep a Changelog" format. Create an "Unreleased" section and a "v3.0.0" section highlighting the transition to a Highload architecture (Redis, Message Queues).

5. **`.github/pull_request_template.md`**
   - A checklist for contributors covering: tests passed, pre-commit passing, docs updated, and a description of changes.

6. **`.github/ISSUE_TEMPLATE/bug_report.yml`** (Use modern GitHub forms format, YAML)
   - Fields: Description, Steps to Reproduce, Expected Behavior, Environment (OS, Python version), and Logs placeholder.

### Formatting Strict Rules
- Output ONLY the requested files.
- Separate each file clearly.
- Use professional, welcoming, and precise English.
- If the output is too long and you need to pause, ask me "Should I continue with the next files?" before proceeding to avoid CLI token truncation.

Begin with the `README.md` and `CONTRIBUTING.md`.