# Quant roles — rebuilt from primary sources

Job-search research covering **73 quant firms** across the EU, UK, Singapore, Hong Kong, Shanghai and Tokyo.
Compiled 4 August 2026. One research pass per firm, reading each firm's own careers page, applicant-tracking
system or public job API.

| File | What it is |
| --- | --- |
| `quant-roles-2026-08-04.xlsx` | **The current sheet.** Six tabs, 753 verified roles. |
| `quant-roles-ranked.xlsx` | The previous version, kept unmodified for comparison. |
| `findings/` | Raw per-firm JSON — the evidence behind every row, including URLs. |
| `RESEARCH_BRIEF.md` | The instructions each firm's research pass followed. |

---

## Scale

| | Previous | Current |
| --- | ---: | ---: |
| Roles | 147 | **753** |
| Verified on the firm's own source | 18 | **~730** |
| Firms | 73 | 73 |

### By track

| Track | Roles |
| --- | ---: |
| C++ | 269 |
| Research | 260 |
| Trader | 128 |
| ML Performance | 96 |

### By location

| Location | Roles |
| --- | ---: |
| London | 260 |
| Shanghai | 115 |
| Hong Kong | 114 |
| Singapore | 86 |
| Amsterdam | 57 |
| Paris | 25 |
| Dublin | 23 |
| Zurich / Zug | 16 |
| Tokyo | 8 |
| Budapest / Warsaw / other | 12 |

---

## Audit of the previous sheet

All 168 previous rows were checked against live sources. **20 survived intact.**

| Verdict | Rows |
| --- | ---: |
| Title does not exist at the firm | 54 |
| Could not verify | 46 |
| No longer open | 39 |
| **Office does not exist** | **9** |
| Confirmed | 20 |

### The nine offices that do not exist

Citadel Securities **Tokyo** · Millennium **Zurich** · WorldQuant **Zurich** · Schonfeld **Zurich** (announced
for later 2026, not open) · Balyasny **Paris** · Mingshi **London** · Jane Street **Chicago** · G-Research
**Dallas** · Old Mission **Amsterdam**

Some appear to originate from empty location records inside a firm's ATS. AQR's applicant system lists a Tokyo
entry with zero jobs that is absent from AQR's own offices page — exactly the shape that becomes a phantom row.

### Other recurring failure modes

- **Invented job titles.** "Core Engineer (C++)" on six Tower Research rows; "Core Platform Engineer" at
  Millennium; "Rust/C++ Engineer" at Wintermute; "Core Software Engineer" at HRT.
- **Inverted eligibility.** Every HRT row was marked student-gated, but that gate applies only to its
  "2027 Grads" reqs. Conversely DRW, Tower, Flow Traders, SIG and IMC rows were marked "recent grads accepted"
  against reqs stating 5-year minimums.
- **Unsourced compensation.** No firm in scope publishes a band for any in-scope city. On the only two rows
  where a real figure existed to compare, the previous sheet was high — Wolverine's posting states a
  **$100–140k** base against **$220–300k** in the sheet; Arrowstreet's states **$155–260k** against
  **$220–300k**.
- **Dead or wrong links.** `cfm.com/careers`, `winton.com/careers`, `mwam.com/careers`,
  `mavensecurities.com/careers`, `voleon.com/careers`, `arrowstreetcapital.com/careers` and `adia.ae/en/careers`
  all 404. The Aquatic row pointed at `aquaticcapital.com`, a parked domain for sale (real site: `aquatic.com`).
  Blackwing's `blackwingam.com` redirects to an unrelated firm.

---

## How the sheet is organised

Sorted by **firm tier**, then **role fit**.

### Firm tier — column A

Comp band and market standing of the firm, for an engineering or research hire.

| Tier | Roles | Firms |
| --- | ---: | --- |
| **S** | 148 | Jane Street, Citadel Securities, Hudson River Trading, Jump, XTX, Radix, Five Rings, PDT, D. E. Shaw, Two Sigma, Renaissance, Headlands, TGS |
| **A** | 353 | Optiver, IMC, SIG, DRW, Tower Research, Flow Traders, G-Research, QRT, Millennium, Point72/Cubist, Balyasny, Squarepoint, Quadrature, Old Mission, Voleon, Vatic, Aquatic |
| **B** | 125 | Schonfeld, ExodusPoint, Verition, Marshall Wace, Man/AHL, Brevan Howard, Systematica, WorldQuant, AQR, Arrowstreet, Winton, Garda, CFM, Akuna, Wolverine, CTC, Belvedere, Maven, Eclipse, Mako, Da Vinci, Virtu, Wintermute, Quantica, Dymon, Quantedge, ADIA, Grasshopper |
| **C** | 109 | Goldman Sachs Strats, Nomura, Webb Traders, All Options, and the larger Chinese managers |
| **D** | 18 | Qianxiang, Blackwing, Chengqi, Mingshi |

> **Basis.** No firm in this dataset publishes a salary band for a European, UK, Singapore, Hong Kong, Shanghai
> or Tokyo seat — checked firm by firm, and the finding was uniform. This tier is therefore **not derived from
> the postings**; it is market consensus, offered as a coarse letter rather than a fabricated number. Treat it
> as a rough ordering, not a pay quote.

### Role fit — column B

What stands between the candidate and the specific role. Visa is deliberately excluded: every location here is
workable (EU and Switzerland by right, Tokyo by residence, UK via self-sponsored HPI, Singapore/Hong Kong
sponsorship routine). There are **no US roles in this dataset**, so H-1B never binds.

| Role fit | Roles |
| --- | ---: |
| Clears gate — apply | 277 |
| Gray zone — ask recruiter | 185 |
| Above band | 143 |
| Mandarin required | 85 |
| Direct match — apply | 41 |
| Blocked — needs enrolment | 11 |
| Confirm source first | 11 |

### Eligibility gates

A recent graduate is neither a student nor a lateral hire, so the grad-adjacent gates are kept apart rather
than collapsed into one verdict.

| Gate | Roles | Meaning |
| --- | ---: | --- |
| Recent-grad window | 11 | "recent graduate", "within two years of graduation", 毕业两年以内 — inside it |
| Campus/grad programme | 38 | No year window stated. Gray zone — worth asking |
| Class-of window | 10 | Names a graduating class that isn't yours. Often soft |
| Student-only (enrolled) | 11 | Requires current enrolment — the only hard exclusion |

---

## Tabs

| Tab | Contents |
| --- | --- |
| **Shortlist** | Firm tier S/A with an apply-now fit — 226 roles |
| **Roles** | All 753, sorted by firm tier then role fit |
| **Old sheet audit** | What each previous row turned out to be, with evidence |
| **Firms & offices** | Per firm: careers URL, confirmed offices, cities checked and not found, how the firm actually hires |
| **Legend** | Column-by-column reference for every value |
| **Method & caveats** | How this was built and what to distrust |

---

## Findings worth knowing

**Tier S + direct match — 13 roles.** Citadel Securities' Quantitative Developer/Research Engineer in Zurich,
London, Hong Kong and Singapore; HRT's three London AI Research Engineer seats; Jane Street's ML Performance
Engineer (London) and ML Engineer (London/HK); Jump's Research Engineer Pre-Training and HPC Operations
(London); XTX's ML Performance Engineer (London).

**The experience gap is the binding constraint.** 143 roles state a years floor above the candidate's band and
59 are campus- or class-gated. Firms with campus reqs on one side and 5-year minimums on the other, and nothing
between, include DRW, Five Rings, Flow Traders, Squarepoint, SIG and WizardQuant. The roles that escape this
gate on demonstrated output instead of tenure, and are disproportionately ML and research seats.

**Shanghai is denser than expected.** 115 roles, second only to London. Five firms have GPU/kernel work there —
Optiver, Minghong (CUDA-PTX operators, TensorRT inference, PyTorch-Triton training), Yanfu (CUDA/Triton/CUTLASS),
WizardQuant and Ubiquant. Language, not eligibility, is the constraint, and it splits by firm: the Shanghai reqs
at Optiver, Tower Research, Eclipse Trading and Man Group state business English only, while High-Flyer,
Ubiquant, Yanfu, WizardQuant, Lingjun and Minghong are Chinese-first.

**Tokyo is thin.** 8 roles total — 4 Trader, 2 Research, 2 Dev — of which 4 clear the eligibility bar. Every one
of the previous sheet's seven Tokyo rows failed the audit. Eleven firms have a confirmed Tokyo office and zero
Tokyo roles. Nomura is a known gap rather than an absence: Japan hires through a separate site that currently
lists nothing.

**Location illusions.** Several roles cover a market from another city, and reading the tag rather than the body
is how a phantom office is born. Flow Traders' Japan-coverage Institutional Trader sits in Hong Kong; Tower's
Japan-flow ETF Trader sits in Singapore; Chicago Trading Company's "Options Trader – Asia Hours" is a Chicago
seat.

**Multi-city requisitions.** Some firms post one req against several cities. Garda's Geneva and Zug listings are
the same requisition, not two seats; likewise Verition's London/Hong Kong/Singapore reqs, Radix's Amsterdam
listings and Headlands' Amsterdam/London pairs. A row per city is kept for searchability, but the underlying
headcount may be one.

---

## Caveats

- **Compensation is mostly empty by design.** Populated only where a figure appeared on the posting or a
  regulator filing. The previous sheet's USD Low/High/Mid columns were dropped rather than carried forward.
- **Gate type and role fit are computed heuristics** over the posting prose, added to make the sheet sortable.
  The verbatim eligibility column is the authority.
- **Citadel Securities rows** were read through a text proxy — the site returns 403 to automated requests. The
  content is the firm's own but was not browser-rendered.
- **Lingjun rows are all secondary-sourced.** Its ATS blocks automated access entirely.
- **Firms that hire through headhunters look emptier than they are** — Marshall Wace, Brevan Howard and
  Quadrature route laterals through direct approaches and standing applications rather than public boards. See
  the *Firms & offices* tab before concluding a firm has nothing.
- **Scope.** Only EU, UK, Singapore, Hong Kong, Shanghai and Tokyo were searched. US-only firms appear with zero
  roles for that reason alone.

## Not yet done

- Firms absent from the original list entirely. Two in-scope locations surfaced that the previous sheet never
  considered — IMC's **Aarhus** office and WorldQuant's **Budapest** seat — so there are likely more firms too.
- Near-scope finds parked rather than included: Maven Securities has two quant reqs in **Monaco**.
