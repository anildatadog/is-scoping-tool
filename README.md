# IS Scoping Tool

AE-facing scoping tool for sizing Datadog Implementation Services engagements.

Walks an AE through 11 business-language questions about a customer opportunity, pre-filled from Salesforce data where possible, and returns a recommended IS methodology with a session estimate and pre-close checklist.

## Local development

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
cp .env.example .env
uv run streamlit run streamlit_app.py
```

First Snowflake query opens a browser for Datadog SSO. Subsequent queries reuse the cached token.

## Project structure

```
streamlit_app.py        # UI: search, questionnaire, result
snowflake_lookup.py     # Snowflake connection + lookup + field mapper
methodologies.py        # QUESTIONS, METHODS, recommend, flags, next steps
scoping_doc.py          # Copy-paste summary formatter
```

## Reference

- Handover doc: [IS Scoping Tool, Claude Code Handover](https://docs.google.com/document/d/1wh13MJalmtK7DrlLyUCW5aM4VEJtQbG0p0pxyXUgJ2U)
- Snowflake query patterns: `dd-governed-onboarding-mcp/.claude/commands/is-salesforce-lookup.md`
- Plan: `~/.claude/plans/velvety-dreaming-spark.md`

## Status

v1: local dev, single-user, copy-to-clipboard output. Deployment target deferred.
