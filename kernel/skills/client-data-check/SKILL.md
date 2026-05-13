---
name: client-data-check
description: Scan a file or directory for personally identifiable information (PII) and other client-sensitive patterns before sharing it with an AI model, posting it somewhere, or committing it. Use whenever the user is about to upload, paste, or commit client material and wants a sanity check. Triggers on phrases like "is this safe to share", "check for PII", "scan this for sensitive data", "co tam je citlivého", "můžu to poslat do API".
---

# Client Data Check

A quick, offline PII / sensitive-data scan. Designed for agency power-users who handle client briefs, exports, transcripts, and datasets — and need a sanity check before that material goes into a model prompt, a public repo, or a screenshare.

This skill does NOT make a legal call about GDPR or data classification. It surfaces patterns that are likely sensitive so a human can decide.

## When to use

- Before pasting a client brief, transcript, or CRM export into a Claude prompt or chat
- Before committing a file that came from a client to a public or shared repo
- Before sharing a screen recording or demo that pulls from real client data
- When the user asks "is this safe to send", "co tam je citlivého", or similar

## When NOT to use

- Code review (use a code review skill instead)
- Compliance audits (this is a sanity check, not an assessment)
- Already-anonymized public datasets

## How it works

The skill runs `scripts/scan.py` against a path. The script applies a set of regex heuristics tuned for Czech and EU context (Czech rodné číslo, IČO, DIČ, IBAN, common Czech phone formats) plus universal patterns (emails, credit cards, API keys, JWTs, AWS keys).

It prints findings as a markdown table: `pattern · count · first match preview · file:line`. No matched values are written to disk — output goes to stdout only, so the report itself is safe to share.

## Step 1: Ask what to scan

Default path is the current working directory. Ask the user to confirm:

> Co mám prověřit?
> 1. Tento soubor: `<path>`
> 2. Celou složku: `<cwd>` (rekurzivně)
> 3. Jiná cesta — řekni jakou

If the user gives a path that doesn't exist, stop and ask again.

## Step 2: Run the scan

```bash
python3 ~/.claude/skills/client-data-check/scripts/scan.py <path>
```

The script handles `.md`, `.txt`, `.csv`, `.json`, `.html`, `.eml`, and other text-like extensions. It skips binaries, `.git/`, `node_modules/`, `dist/`, and files over 5 MB (those need their own treatment).

## Step 3: Interpret the result

Report to the user in plain language, not raw regex output:

- **No findings:** "Žádné typické citlivé vzorce jsem nenašel. To neznamená, že tam nic není — kontext (např. interní strategie, ceník) regex nezachytí. Posoudit musíš ty."
- **Findings present:** List each pattern category in plain Czech, with count and the file paths involved. Do NOT print matched values back to the user — print `file:line` references so they can open the spot themselves.

Example output to the user:

> Našel jsem:
> - 3× e-mail v `docs/brief.md` (řádky 12, 45, 78)
> - 1× telefon v `docs/brief.md` (řádek 14)
> - 1× IČO v `clients/acme.csv` (řádek 3)
>
> Posuď, jestli to chceš poslat ven. Pokud ne, anonymizuj zdroj a spusť scan znovu.

## Step 4: Suggest next step

After reporting:
- If findings: offer to help draft an anonymized version (replace names, emails, phones with `<NAME>`, `<EMAIL>`, etc.) — only if the user asks. Don't do it automatically.
- If clean: end the skill. Don't offer to "scan again with more rules" or similar.

## What the scan covers

Patterns the script looks for:

| Category | What it matches |
|----------|-----------------|
| Email | Anything resembling `name@domain.tld` |
| Phone (CZ) | `+420 XXX XXX XXX`, `XXX XXX XXX`, `XXX-XXX-XXX` |
| Phone (international) | `+NNN ...` with at least 7 digits after country code |
| Rodné číslo | `YYMMDD/XXXX` or `YYMMDDXXXX` patterns |
| IČO | 8-digit identifiers preceded by `IČ`, `IČO`, or in a context likely to be a company ID |
| DIČ | `CZ` followed by 8–10 digits |
| IBAN | `CZ` or other EU country IBAN format |
| Credit card | Luhn-passing 13–19 digit sequences |
| API key (generic) | High-entropy strings of 32+ chars near tokens like `key`, `secret`, `token`, `password` |
| AWS access key | `AKIA[0-9A-Z]{16}` |
| Anthropic API key | `sk-ant-api03-...` and similar |
| OpenAI API key | `sk-...` of OpenAI key length |
| JWT | Three base64 segments separated by dots |
| Czech address (heuristic) | Street + number + postal code pattern |

The script tags each match with its category and never echoes the matched value to its own output — only `file:line` and a redacted preview (`a***@d***.cz`).

## Limitations (tell the user)

- **Regex catches form, not meaning.** A regex can flag a fake number that looks like rodné číslo, or miss real client data that doesn't follow the pattern.
- **Context isn't scanned.** A client's strategic plan, internal pricing, or unflattering quotes are sensitive — but no regex catches them. The user is still the judge.
- **Encrypted / binary content is skipped.** PDFs, DOCX, XLSX, images are not parsed. Convert them to text first if needed.
- **Scope is the file system.** Already-pasted-into-Claude content can't be unscanned; this skill is a pre-flight check, not a recall mechanism.

## Output policy

- Never print matched values in full to the chat — only redacted previews and file:line refs.
- Never write a report file to disk by default. If the user asks for one, write to `client-data-check-<YYYY-MM-DD>.md` in the working directory, and remind them not to commit it.
