# Quant role research brief

You are researching **one firm** for a job search. Read this whole file before starting.

## Candidate profile (who the roles are for)

- EPFL MSc, graduated Feb 2026. Currently employed in Tokyo (~18 months experience by a mid-2027 start).
- First-author papers under review (ICLR x2, AAAI), ISCA workshop publication.
- Merged GPU kernels in llama.cpp; production C++.
- **Not** a new-grad/student any more. Student-gated and "graduating in <year>" reqs are a poor fit — note the gate when you see one.

Work authorisation:
- **EU citizen** — Paris, Amsterdam, Dublin, Warsaw, Milan, Frankfurt etc: no sponsorship needed.
- **CH residence permit** — Zurich, Zug, Geneva, Pfäffikon: no sponsorship needed.
- **JP residence** — Tokyo: already in-country.
- **UK** — eligible for the High Potential Individual visa, self-sponsored, costs the employer nothing.
- **Hong Kong / Singapore / Shanghai** — needs sponsorship, routine at these comp levels. Mainland China seats are usually Mandarin-first; flag if a role is an English-tolerant exception.

## Scope — what to look for

**Locations (ONLY these):** anywhere in the **EU**, the **UK**, **Singapore**, **Hong Kong**, **Shanghai**, **Tokyo**.
Ignore US, Canada, India, Middle East, Australia and other offices entirely — they are out of scope for this pass.

**Tracks (ONLY these four):**
1. `C++` — low-latency / systems / core infrastructure / trading systems / quant developer where the work is C++.
2. `ML Performance` — ML engineering, ML infrastructure, GPU/HPC/kernel work, research engineering.
3. `Trader` — trader, junior trader, algo trader, quantitative trader, execution trader.
4. `Research` — quantitative researcher, quant analyst, ML researcher, strategist.

Anything else (sales, compliance, IT support, pure Python data eng, internships lasting <6 months) is out of scope.

## Method — how to research

1. Find the firm's **own careers page**. Prefer the firm's domain over aggregators. Many firms use Greenhouse/Lever/Workday — a `boards.greenhouse.io/<firm>` or `<firm>.wd1.myworkdayjobs.com` page hosted for that firm counts as primary.
2. Enumerate live openings in the in-scope locations and tracks. Read the actual posting where you can.
3. For each opening, capture the exact title, city, and a **direct URL**.
4. Also check the firm's own **offices/locations page** to confirm which in-scope cities the firm actually has. This matters: a previous version of this sheet invented a "Tower Research Tokyo" office that does not exist.

## Anti-fabrication rules — read twice

This sheet has already been burned once by invented data. Accuracy beats coverage.

- **Never invent a role, office, URL, or compensation figure.** An empty result is a good result if the firm genuinely has nothing open.
- Only mark `verification: "verified-primary"` if you personally loaded the firm's own site/careers page/posting and saw the role. Include the URL you saw it on.
- Use `verification: "reported-secondary"` when you only have press, LinkedIn, community posts, or an aggregator.
- Use `verification: "office-unconfirmed"` when you could not confirm the firm even has an office in that city.
- If a page was unreachable (blocked, JS-only, 403), say so in `notes` rather than guessing what was behind it.
- Compensation: only give a figure if you saw it stated (posting, regulator filing, levels.fyi). Otherwise leave `comp_local` empty. Do not extrapolate from other firms.

## Also: audit the existing rows

You will be given the rows already in the spreadsheet for your firm. For each one, check whether it still holds:
- Does that office exist? Is a role of that track plausibly/actually open there?
- Is the title right?
- If the row is wrong or the office does not exist, say so explicitly.

## Output

Write **one JSON file** to `/home/mujin/workspaces/quant/findings/<slug>.json` where `<slug>` is given in your task prompt. Exact shape:

```json
{
  "firm": "Firm Name",
  "careers_url": "https://...",
  "offices_in_scope_confirmed": ["London", "Amsterdam", "Singapore"],
  "offices_checked_not_found": ["Tokyo"],
  "roles": [
    {
      "location": "London",
      "title": "Exact title as posted",
      "track": "C++ | ML Performance | Trader | Research",
      "url": "https://direct-link-to-req",
      "verification": "verified-primary | reported-secondary | office-unconfirmed",
      "live_as_of": "2026-08-04",
      "eligibility": "what the posting says about experience/graduation-year gates, verbatim if short",
      "requirements": "3-6 short bullets of the stated requirements, separated by ' | '",
      "comp_local": "only if stated somewhere credible, else empty string",
      "notes": "anything the candidate should know: visa language, Mandarin requirement, team, etc."
    }
  ],
  "existing_rows_audit": [
    {
      "location": "Tokyo",
      "existing_title": "Platform Engineer",
      "verdict": "confirmed | title-changed | no-longer-open | office-does-not-exist | could-not-verify",
      "detail": "one sentence of evidence, with URL where possible"
    }
  ],
  "notes": "anything about the firm's hiring process, blocked pages, or coverage gaps in your research"
}
```

Rules for the file:
- Valid JSON, UTF-8, no trailing commas, no markdown fences around it.
- If the firm has no in-scope openings, still write the file with `"roles": []` and explain in `notes`.
- Do not touch any file other than your own findings file.

## Final message

Keep your final response under 10 lines: firm name, how many roles you added, how many existing rows you flagged as wrong, and any blocker. The JSON file is the real deliverable.
