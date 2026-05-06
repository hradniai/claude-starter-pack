<purpose>
{{PROJECT_NAME}}: {{ONE_LINE_DESCRIPTION}}
</purpose>

<project>
- Status: {{draft | prototype | mvp | production | archived}}
- Tech stack: {{TECH_STACK}}
- Deploy target: {{WHERE — optional, fill when known}}
</project>

<architecture>
{{KEY_DECISIONS — fill as project evolves}}
</architecture>

<development>
## Run locally
{{HOW_TO_RUN}}

## Dependencies
{{KEY_DEPENDENCIES}}
</development>

<documentation>
Per-feature documentation — every concern gets its own file in docs/features/.
One page = one MD file. Larger topics = subdirectory. Mix granularity freely.
Doc changes belong in the same commit as code changes.
</documentation>
