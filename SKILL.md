# SKILL: multi-agent job-market research

How this repo was built, precisely enough for another Claude instance to extend it without repeating the
mistakes. This is the shared method document for both `quant-roles` and `tech-roles`; paths in the examples
use the tech repo but apply identically here (this repo additionally uses `existing/` and the
`existing_rows_audit` field, since it audited a prior spreadsheet). Written 5 August 2026, after two full runs: `quant-roles` (73 firms, 753 roles) and this one
(63 firms role-extracted, 605 roles, 354-firm discovery landscape).

Read this before spawning anything.

---

## 1. The core problem this method solves

The first version of the quant sheet was AI-generated without primary-source verification. Auditing its 147
rows against live careers pages found **20 survived intact**. The failure modes were not random:

| Failure | Count | Example |
| --- | ---: | --- |
| Job title exists nowhere at the firm | 54 | "Core Engineer (C++)" on six Tower Research rows |
| Could not verify | 46 | |
| Role no longer open | 39 | |
| **Office does not exist** | 9 | Citadel Securities Tokyo; Millennium Zurich; Mingshi London |
| Confirmed | 20 | |

Plus: every compensation figure was unsourced, and on the two rows where a real published figure existed to
compare against, the sheet was **high** (Wolverine claimed $220–300k against a posted $100–140k base).

**The whole method exists to prevent that.** Every design decision below traces back to it.

---

## 2. Architecture

### Two phases, and why

**Quant run** had a firm list already (the existing spreadsheet), so it went straight to one agent per firm.

**Tech run** had no list, so it needed:
1. **Discovery** — one agent per *region*, building a firm list with tiers and careers URLs. Cheap, broad, no
   deep role enumeration.
2. **Extraction** — one agent per *firm* (or per small themed group), reading every in-scope req.

Discovery counts are **unreliable and systematically low**: Humanoid showed ~8 roles on a JS first page and
**78** via the API; Arm's discovery count of 167 UK openings was really ~69. Treat discovery numbers as
"worth a look" signals, never as data. Only per-firm extraction produces rows.

### Grouping

Single-firm agents for anything large (Arm, Apple, Google, Amazon). Group 2–4 small related firms into one
agent to save slots — `swiss-robotics.json`, `japan-silicon.json`, `france-defence.json`. Grouped agents write
a **JSON array** of firm objects instead of a single object; the merge script handles both.

### Concurrency

Hard cap of **20 concurrent subagents** (`CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`). Excess launches fail
immediately with a clear error — they do not queue. Keep a `QUEUE.json` recording running / queued / parked,
and launch a replacement each time a completion notification arrives.

---

## 3. The research brief

Both runs put the shared instructions in a `RESEARCH_BRIEF.md` at the repo root and gave each agent a
three-line prompt pointing at it. This is much better than inlining instructions per agent: one edit updates
every subsequent agent, and the prompts stay short.

The brief must contain:

1. **Candidate profile** — background, and *work authorisation per country*, because that determines which
   locations are real options.
2. **Scope: locations** — an explicit allow-list, and an explicit "ignore everything else".
3. **Scope: tracks** — with a test for edge cases, not just a list. The C++/Systems track needed
   *"the test is whether the work is systems work — performance, concurrency, resource management, the machine
   underneath — not which subsystem it sits in"*, because agents were otherwise excluding distributed-systems
   roles.
4. **Scope: domain** — what to exclude even when the title says "engineer".
5. **Tier definitions** with worked examples.
6. **Method** — find the firm's own board; ATS boards hosted for the firm count as primary; confirm the office
   on the firm's own site, never from a job board's location tag.
7. **Anti-fabrication rules** (see §4).
8. **Exact output JSON schema.**
9. **"Final message under 10 lines"** — the JSON file is the deliverable; long summaries waste the orchestrator's
   context.

### Updating the brief mid-run

When scope changes, edit the brief *and* resume already-finished agents with `SendMessage` — they retain full
context and top up cheaply. Widening the C++/Systems track this way added 18 roles across five firms for a
fraction of a re-run. See §7 for the exact message.

---

## 4. Anti-fabrication protocol

This is the part that matters. Verbatim from the brief:

```
- Never invent a role, office, URL, funding figure or compensation number.
- verified-primary only if you personally loaded the firm's own site or board and saw it. Include the URL.
- reported-secondary for press, LinkedIn, community or aggregator sourcing.
- office-unconfirmed if you could not confirm the firm has an office in that city.
- If a page was unreachable (403, JS-only, blocked), say so in notes rather than guessing.
- Compensation: only if stated on the posting or a regulator filing. Otherwise leave empty.
- An empty result is a good result if the firm genuinely has nothing open.
```

That last line matters more than it looks. Without it agents pad.

**Tell agents about a known past fabrication.** The quant brief named the invented "Tower Research Tokyo"
office. Agents then proactively checked office lists and caught eight more phantoms.

### Verify conflicting agent claims yourself

Agents contradict each other and occasionally retract *correct* findings. One "verification" agent reported
AMD UK had 3 roles, contradicting two other sources saying 16. A single direct API call settled it at 16 —
the retraction was wrong.

```bash
curl -sS 'https://careers.amd.com/api/jobs?country=United%20Kingdom&limit=100' | python3 -c "..."
```

**When two agents disagree on a fact you have already relayed to the user, check it yourself.** It is usually
one cheap call.

---

## 5. Location illusions — the highest-yield trap class

Roles that cover a market from another city. Reading the tag instead of the body is how phantom offices are
born. Real examples found:

- Flow Traders' Japan-coverage Institutional Trader **sits in Hong Kong**
- Tower Research's Japan-flow ETF Trader **sits in Singapore**
- Chicago Trading Company's "Options Trader – Asia Hours" is a **Chicago** seat
- OpenAI has a Singapore-tagged req whose body says **San Francisco**
- Wayve's Japan office is **Yokohama**, not Tokyo
- Axelera's Ashby board tags **up to ~58 cities per requisition**; only 3 are real offices
- AQR's ATS lists a **Tokyo entry with zero jobs** that is absent from AQR's own offices page — this is likely
  the mechanism behind several phantom offices in the original quant sheet

Instruction that works: *"confirm from the firm's own site that it actually has an office in the city you are
claiming. Do not infer an office from a job board's location tag."*

Also watch for **wrong-firm** errors: `turing.com` (Palo Alto) vs `tur.ing` (Tokyo); `humanoid.co.uk` (a video
agency) vs `thehumanoid.ai`; Blackwing's site 301-redirecting to an unrelated company; Aquatic's cited domain
being a parked GoDaddy sale page.

---

## 6. ATS cookbook

Most careers pages are JS shells. The underlying ATS almost always has a readable endpoint. This cookbook was
assembled from ~90 agent runs and is the single biggest time-saver.

| ATS | How to read it |
| --- | --- |
| **Greenhouse** | `boards-api.greenhouse.io/v1/boards/<token>/jobs?content=true` — full text, no auth |
| **Lever** | `api.lever.co/v0/postings/<token>?mode=json` |
| **Ashby** | `jobs.ashbyhq.com/<org>` + its GraphQL endpoint; posting API returns all live reqs |
| **Workday** | `<tenant>.wdN.myworkdayjobs.com/wday/cxs/<tenant>/<board>/jobs` (POST for some tenants) |
| **SmartRecruiters** | public API; used for CERN |
| **Eightfold / PCSX** | `apply.careers.microsoft.com/api/pcsx/search`; some tenants auth-gate it (Qualcomm) |
| **Avature** | paginate with `?jobOffset=` (Two Sigma) |
| **HERP** | `herp.careers/v1/<org>` (Japanese firms: Turing, Fixstars, TIER IV) |
| **MokaHR** | Chinese/Japanese boards; **AES-encrypted payloads** — decryptable (High-Flyer, Ubiquant) |
| **Talentio** | job JSON embedded in `data-react-props` (Preferred Networks) |
| **BambooHR / Recruitee / Workable / Pinpoint / Umantis / PageUp / Jibe / Beisen / Feishu** | all have JSON routes; Pinpoint exposes `jobs.rss` with full bodies |
| **Gatsby sites** | `page-data.json` often reveals an Algolia app ID + index (u-blox) |
| **Relay/Next.js** | replay the page's own query — Meta's `CareersJobSearchResultsDataQuery` with its `doc_id` |
| **Google careers** | full results embedded server-side in `AF_initDataCallback` |
| **Point72** | live feed embedded in page source as the `CSSearchModule.init()` argument |
| **ASP.NET postback** | replaying `__doPostBack` yields stable `detail.aspx?id=` URLs (NTT) |

Other tricks that worked:
- A JS careers page's **JS bundle** often names the backing board (`/js/job-search.js` → Greenhouse token, Flow Traders)
- **Jane Street** obfuscates titles with Lisu homoglyphs in `janestreet.com/jobs/main.json` — de-homoglyph and cross-check
- **Cloudflare 403 to fetchers** often serves 200 to a browser User-Agent via `curl` (Cadence, Fractile)
- When a **global English careers page 403s, the Japanese recruit subdomain usually loads** (`-recruit.jp`, `hrmos.co`, `jposting.net`)
- `r.jina.ai` text proxy as a last resort — mark those rows a notch lower, content is primary but not browser-rendered

### Count traps

- **Synopsys** `/search-jobs/United%20Kingdom` advertises "111 jobs"; the country facet reads UK (1), US (110). It is keyword matching, not location filtering.
- **Graphcore's** own marketing page says "No vacancies open right now" while its Greenhouse board carries **219**.
- **Arm's** default UK search returns "394 results" of which 279 are jobs and most are not UK.
- **DeepMind's** board location filter matches primary location only and hides multi-location reqs — read each detail page's location array.

---

## 7. Prompt templates

### Discovery (one per region)

```
Read <REPO>/RESEARCH_BRIEF.md for the candidate profile, tracks, tier definitions and anti-fabrication rules.

Your job is DISCOVERY, not role extraction. Build the firm list for **<REGION>**.

Find companies that (a) have a real engineering presence in <REGION>, and (b) hire for <TRACKS>.
Cover every tier:
- T1 <examples>
- T2 <examples>
- T3 <examples>
- T4 <examples — name 2-3 archetypes the user cares about>

EXCLUDE <out-of-scope categories>.

For each firm record: name, tier, tier_reason (for startups: funding round/amount/date/investor),
careers URL, whether an engineering office is confirmed on the firm's OWN site, and a rough count of
in-scope live openings if cheaply visible. Do not deeply enumerate roles — that is a later pass.

Write to <REPO>/discovery/<region>.json as:
{"region":"","firms":[{"name":"","slug":"","tier":"","tier_reason":"","careers_url":"",
 "office_confirmed":true,"cities":[""],"approx_in_scope_roles":0,"notes":""}],"notes":""}

Aim for breadth — 25-40 firms. Valid JSON, no markdown fences. Final message under 10 lines.
```

Ask Hong Kong-style thin regions to *"report honestly if the landscape is thin — a short accurate list is more
useful than a padded one"*. That produced the correct and valuable finding that HK big-tech offices hold zero
engineering roles.

### Per-firm extraction

```
Read <REPO>/RESEARCH_BRIEF.md in full and follow it exactly — note <any recent brief changes>.

Your firm: **<NAME>** (slug: `<slug>`)
Existing rows for this firm: <REPO>/existing/<slug>.json      ← only when auditing a prior sheet
Write your findings to: <REPO>/findings/<slug>.json

Focus locations: <list>. <One or two sentences of firm-specific steer: which org to cover, a known
trap, what a prior pass found and should be verified.>

Note: a session-wide WebSearch budget is exhausted — use direct fetches.
```

**Firm-specific steer is what makes these work.** Compare a bare prompt against:
*"A discovery pass found ~14 in-scope openings and noted a trap: Graphcore's own marketing page says 'no
vacancies' while its Greenhouse board is live. Use the board, not the marketing page."* The second found 19
roles; a verification agent using the marketing page reported 0.

### Top-up after a scope change

```
The <track> definition has been widened. Please top up your <FIRM> findings file.

Newly in scope: **<definition>**. <One-sentence test for edge cases.>

Re-scan the in-scope reqs you already enumerated and add any you excluded under the narrower reading —
<concrete examples of what to look for>. Keep track "<track name>".

Append to <path>, preserving the existing entries. Reply with just the count added.
```

### Resume after an API stall

Agents fail with `Response stalled mid-stream`. If the agent had made progress, **resume rather than
relaunch** — it keeps its context and partial work:

```
Your run was cut off by an API stall, not by anything you did. Please pick up where you left off.

You had <state> and were moving on to <next>. Continue from there and finish <scope>, then write to <path>.

If you are short on budget, prioritise in this order: <ordered list>. A partial file covering the first
two well is more useful than four thin entries.
```

### Verification pass

Run these *separately* from extraction — they need a different mindset:

```
Your job is a VERIFICATION pass, not role extraction. <What is unverified and why.>

Read <files> and collect every firm marked <tier> whose tier_reason says funding was not verified.
For each, verify from the firm's OWN newsroom/press/about page — direct fetch, no search engines.
Capture: round name, amount, currency, date, lead investor(s), and the URL you read it on.
Where the firm publishes nothing, say so explicitly rather than guessing — "not published on own site"
is a valid and useful result.

Then re-assess the tier: <criteria>. <Name two calibration points.>
```

This pass caught both wrong-firm errors and recommended six tier changes.

---

## 8. Output schema

```json
{
  "firm": "Firm Name",
  "firm_tier": "T1..T5",
  "tier_reason": "for T4: round, amount, date, lead investor",
  "careers_url": "https://...",
  "offices_in_scope_confirmed": ["London"],
  "offices_checked_not_found": ["Tokyo"],
  "roles": [{
    "location": "", "title": "", "track": "", "domain": "",
    "url": "", "verification": "verified-primary|reported-secondary|office-unconfirmed",
    "live_as_of": "YYYY-MM-DD",
    "eligibility": "verbatim if short", "requirements": "3-6 bullets separated by ' | '",
    "comp_local": "only if stated", "notes": ""
  }],
  "existing_rows_audit": [{"location":"","existing_title":"","verdict":"","detail":""}],
  "notes": ""
}
```

`existing_rows_audit` is only for runs auditing a prior sheet. Verdicts used:
`confirmed | title-changed | no-longer-open | office-does-not-exist | could-not-verify`.

Grouped agents emit an **array** of these objects. `tools/merge.py` handles both shapes.

---

## 9. Merge pipeline

`tools/` contains everything; **no third-party packages** (this environment has no `openpyxl` — PEP 668 blocks
pip and the venv has no pip, so both readers and writers are stdlib-only).

| File | Purpose |
| --- | --- |
| `tools/xlsx_read.py` | Minimal xlsx reader — also the round-trip validator |
| `tools/xlsx_write.py` | Minimal xlsx writer: multi-sheet, frozen bold header, autofilter, column widths, wrapped text |
| `tools/merge.py` | Reads `findings/*.json` + `discovery/*.json`, computes derived columns, writes the workbook |

```bash
cd tools && python3 merge.py          # rebuild after any new findings file
```

Always validate by round-tripping:

```python
from xlsx_read import read
import zipfile
d = read(path); zipfile.ZipFile(path).testzip() is None
```

### Derived columns

Computed heuristics over posting prose, existing only to make the sheet sortable. **The verbatim eligibility
column is always the authority** — say so in the Legend.

- **Firm tier** — a lookup table, not inferred. Comp band / market standing.
- **Role fit** — combines gate, language and verification.
- **Experience gate** — regex classification of the eligibility text.
- **Language** — Japanese/Mandarin/French detection.
- **Work authorisation** — city → status, from the candidate's passport and permits.

### Three heuristic bugs found the hard way

1. **Negation.** Postings say *"No student or graduation-year gate"*. Matching the bare words inside that
   sentence inverts its meaning — it flagged 49 explicitly-ungated roles as gated, including tier-S candidates.
   **Check negation first, always.**
2. **Title-only signals.** Seniority and graduate programmes are often stated only in the title
   ("Quantitative Researcher – Graduate: 2027", "Performance Engineering Manager"). Classify the title
   separately from the body, and let an explicit years figure in the body outrank a title guess.
3. **Notes contamination.** Researcher commentary discusses gates in order to explain them (*"the experienced
   reqs redirect recent grads here, which confirms the gate is real"*). Reading `notes` as posting text
   inverted the meaning. **Classify from `eligibility` + `requirements` only.**

**Known unfixed flaw:** firm-level language constraints are not caught per-role. Fixstars and PEZY roles read
as "apply-now" although both firms are Japanese-only (no English careers site at all). Japan's true
English-workable set is ~14 roles, not 35. A firm-level language override in `merge.py` would fix it.

---

## 10. Tiering honestly

The user asked for firm tiers "by salary band". **No firm in either dataset published a band for a non-US
seat** — checked firm by firm, uniformly. So:

- A **tier letter** is a defensible coarse judgement and is offered as such.
- **Specific numbers are not**, and the original sheet's invented USD Low/High/Mid columns were dropped rather
  than carried forward.
- State the basis in the Legend, at the top, before anyone relies on it.

The `comp_local` column holds only figures that actually appeared on a posting or a regulator filing. Where a
US dollar band appears on a non-US req it is a US pay-transparency disclosure that does not describe the local
package — label it.

---

## 11. Failure modes seen

| Mode | Handling |
| --- | --- |
| `Response stalled mid-stream` | Resume via `SendMessage` if progress was made; relaunch if not |
| Concurrency cap | Launches fail immediately, do not queue — track in `QUEUE.json` |
| WebSearch quota exhausted session-wide | Direct fetches proved *better*; tell agents up front so they do not waste calls |
| Agent retracts a correct finding | Verify yourself with one call (§4) |
| Agent invents a summary while children still run | Ignore unsourced summaries; trust only tool-cited claims |
| Shared `/tmp` clobbering between agents | Use per-agent scratch paths |
| Stale wait-timer notifications | Harmless; a completed agent may notify repeatedly |

---

## 12. Continuing this work

1. Read `QUEUE.json` for parked items.
2. `discovery/*.json` holds **354 firms**; **63** are role-extracted. Everything in `findings/` is done —
   anything in discovery without a matching findings file is available work.
3. Pick high `approx_in_scope_roles` firms first, but re-verify the count.
4. Follow §7's per-firm template, adding a firm-specific steer.
5. `cd tools && python3 merge.py`, then round-trip validate.
6. Update `README.md` counts and any new traps.

### Known open items

- **MBDA** — Cloudflare-blocked; 451 live French postings, ~22 title-only FPGA/ASIC leads. Needs a browser.
- **Bot-blocked, unread**: Intel, Broadcom, Cadence, Siemens EDA, Infineon, NXP, Analog Devices, TI, ST (UK);
  Denso, Omron, Fujitsu, Sony Semiconductor, JASM (Japan).
- **58 Japan roles** tagged "Check — Japan seat" — language unresolved.
- **US pass** never run for this landscape. For a US pass, note the candidate is an EU citizen: TN, E-3 and
  H-1B1 are country-locked and unavailable; the routes are H-1B lottery, **O-1A** (publications and OSS are the
  qualifying evidence), **L-1B** after a year at a firm's non-US office, and self-petitioned EB-1A/NIW. The
  L-1 route makes a firm's European or Asian office a deliberate stepping stone.
- The parallel **`quant-roles`** repo uses the same method and tooling.

### Candidate-specific facts that shaped the search

Keep these current — several conclusions depend on them:

- French national → EU freedom of movement; **CERN Member State**; **clears French defence/aerospace
  nationality and clearance gates**; French-language postings are an *advantage*, not a barrier.
- Swiss residence permit → Zurich/Geneva/Lausanne need no sponsorship.
- Japanese residence → Tokyo needs no visa step, but **Japanese language is the real gate**.
- UK HPI eligibility → self-sponsored, costs the employer nothing. Say so in applications; 13 of 26 Graphcore
  reqs say "unable to provide visa sponsorship", which HPI satisfies anyway.
- Feb-2026 MSc, ~18 months by a mid-2027 start → **above graduate schemes, below most lateral bars.** This is
  the single most important constraint. Target reqs that gate on *evidence* (publications, open-source)
  rather than tenure — merged llama.cpp GPU kernels and a hand-written C compiler are the evidence.
