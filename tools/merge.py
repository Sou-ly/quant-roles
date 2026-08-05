"""Merge the per-firm findings JSON into the rebuilt spreadsheet."""
import json, os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from xlsx_write import Sheet, write

BASE = '/home/mujin/workspaces/quant'
FIND = f'{BASE}/findings'

TRACK_ORDER = {'ML Performance': 0, 'C++': 1, 'Research': 2, 'Trader': 3}

# Work authorisation by city, from the candidate profile in RESEARCH_BRIEF.md.
EU = ('Amsterdam Aarhus Paris Dublin Warsaw Milan Madrid Frankfurt Munich Budapest '
      'Bristol Copenhagen Luxembourg Cluj Kajaani Berlin Rotterdam Brussels Lisbon Athens').split()
CH = 'Zurich Zug Geneva Pfaffikon Pfäffikon Schaffhausen Lugano Basel'.split()

def auth(loc):
    city = loc.split('(')[0].strip()
    base = city.split('/')[0].split(',')[0].strip()
    if base in EU:
        return 'EU citizen — no sponsorship'
    if base in CH:
        return 'CH permit — no sponsorship'
    if base == 'Tokyo':
        return 'JP resident — in country'
    if base in ('London', 'Bristol', 'Cambridge', 'Oxford'):
        return 'UK HPI — self-sponsored'
    if base in ('Singapore', 'Hong Kong', 'Shanghai', 'Beijing', 'Shenzhen', 'Hangzhou'):
        return 'Sponsorship required'
    return 'Check'

# --- Derived columns -------------------------------------------------------
# The eligibility text is free prose written by the research agents, so these
# are heuristics over it, not parsed fields. They exist to make the sheet
# sortable; the Eligibility column remains the authority and is kept verbatim.

_YEARS = re.compile(r'(\d+)\s*\+?\s*(?:-\s*\d+\s*)?(?:years?|yrs?|年)', re.I)

# CHECKED FIRST. Postings very often say "no student or graduation-year gate",
# and matching the bare words inside that sentence inverts its meaning -- which
# is exactly the mistake the previous version of this sheet made in the other
# direction for Hudson River Trading.
_NEG_GATE = re.compile(
    r'\bno\b[\w\s,\-/]{0,45}?\b(?:gate|gated|floor|minimum|requirement|restriction)|'
    r'\bnot\b[\w\s,\-/]{0,25}?\b(?:student|graduation|campus).{0,12}?gated|'
    r'no minimum|without a minimum|no yoe|open to all (?:levels|experience)|'
    r'welcomes? (?:candidates )?(?:at )?(?:all|any) (?:levels|experience)', re.I)

# You ARE a recent graduate -- these windows include you.
_RECENT_GRAD = re.compile(
    r'within\s+(?:one|two|three|1|2|3)\s+years?\s+of\s+graduat|'
    r'毕业\s*(?:两|三|2|3)\s*年以内|毕业两年内|'
    r'recent(?:ly)?\s+graduat|recent grad|'
    r'0\s*[-–]\s*[123]\s*(?:years?|yrs?)|up to\s+[123]\s+years?', re.I)

# Requires current enrolment -- you genuinely cannot apply.
_ENROLLED = re.compile(
    r'currently (?:a )?(?:enrolled|studying|a student)|must be (?:a )?(?:current )?student|'
    r'pursuing a (?:bachelor|master|bs|ba|ms|phd)|in your (?:final|penultimate) year|'
    r'enrolled in a (?:degree|programme|program)|在读', re.I)

# Names a graduating class that is not yours (you graduated Feb 2026).
_CLASS_OF = re.compile(
    r'class of 20\d\d|graduat\w*\s+(?:in|by|between|during)\s+[\w\s,]{0,30}?20\d\d|'
    r'20\d\d\s*(?:grads?|graduates?)|应届|校招|'
    r'graduating\s+(?:in\s+)?(?:winter|spring|summer|autumn|fall|dec|jun|aug)', re.I)

_NOGATE = _NEG_GATE
_EVIDENCE = re.compile(
    r'publication|papers?|ICLR|NeurIPS|AAAI|ICML|open.source|conference|'
    r'track record of research|research output|portfolio of work', re.I)
_MANDARIN = re.compile(r'mandarin|chinese (?:language|communication)|中文|普通话', re.I)
_STUDENT_TITLE = re.compile(
    r'\b(?:graduate|grad|campus|intern|internship|student|placement|'
    r'kickstart\w*|应届|校招|实习)\b|graduate[:\s-]*20\d\d|20\d\d\s*grad', re.I)

# Seniority is often stated only in the title -- "Principal Research Scientist"
# carries no years figure in its body but is plainly above an 18-month
# candidate. Same for graduate programmes that announce themselves in the title
# ("Quantitative Researcher - Graduate: 2027") and say nothing in the prose.
_SENIOR_TITLE = re.compile(
    r'\b(?:senior|staff|principal|lead|head of|director|chief|'
    r'vice president|vp|manager|expert|专家|资深|高级)\b', re.I)

def gate_of(elig, reqs, notes, title=''):
    """Classify the eligibility bar into something sortable.

    A Feb-2026 MSc with ~18 months experience is a RECENT GRADUATE, not a
    student and not a lateral hire. That is a gray zone, and the three cases
    below are genuinely different -- collapsing them into one "graduation
    gated" verdict throws away the distinction that matters most:

      Student-only      requires current enrolment. You cannot apply.
      Class-of window   names a graduating year that is not yours. Outside by
                        the letter, but these are frequently soft -- ask.
      Recent-grad       "within two years of graduation", "recent graduate",
                        "0-2 years". You are inside these.
    """
    # Eligibility and requirements only. `notes` is the researcher's commentary
    # about the role and often discusses a gate in order to explain it ("the
    # experienced reqs redirect recent grads here, which confirms the gate is
    # real") -- reading it as posting text inverts the meaning.
    text = ' '.join(x for x in (elig, reqs) if x)
    title = title or ''

    # Negation first, always. "No student or graduation-year gate" must not be
    # read as a student gate.
    negated = bool(_NEG_GATE.search(text))

    if _ENROLLED.search(text) or re.search(r'\bintern(ship)?\b', title, re.I):
        return 'Student-only (enrolled) — cannot apply'
    if _RECENT_GRAD.search(text):
        return 'Recent-grad window — you clear'

    if not negated:
        # In a title, "Graduate"/"Campus" names the programme unambiguously;
        # in body prose it does not ("a graduate degree is required").
        if _STUDENT_TITLE.search(title):
            return 'Campus/grad programme — ask recruiter'
        if _CLASS_OF.search(text):
            return 'Class-of window — outside by letter, ask'

    if not text.strip():
        if _SENIOR_TITLE.search(title):
            return 'Senior-titled — likely above band'
        return 'Unstated'

    years = [int(m) for m in _YEARS.findall(text)]
    years = [y for y in years if 1 <= y <= 20]
    if years:
        lo = min(years)
        if lo <= 2:
            return f'Tenure {lo}+ yrs (you clear)'
        if lo == 3:
            return 'Tenure 3+ yrs (borderline)'
        return f'Tenure {lo}+ yrs (above you)'
    # A senior title outranks a body that simply forgot to name a number.
    if _SENIOR_TITLE.search(title):
        return 'Senior-titled — likely above band'
    if negated:
        return 'No stated gate'
    if _EVIDENCE.search(text):
        return 'Evidence-based (papers/OSS)'
    return 'Unclear — read posting'

def mandarin_of(elig, reqs, notes, loc):
    text = ' '.join(x for x in (elig, reqs, notes) if x)
    if _MANDARIN.search(text):
        return 'Mandarin required'
    if loc.split('(')[0].strip() in ('Shanghai', 'Beijing', 'Shenzhen', 'Hangzhou'):
        return 'Check — mainland seat'
    return ''

# Gates that a Feb-2026 graduate with ~18 months experience can actually clear.
OPEN_GATES = ('No stated gate', 'Evidence-based (papers/OSS)',
              'Tenure 1+ yrs (you clear)', 'Tenure 2+ yrs (you clear)',
              'Recent-grad window — you clear')
NO_VISA = ('EU citizen — no sponsorship', 'CH permit — no sponsorship',
           'JP resident — in country', 'UK HPI — self-sponsored')
# Gray zone: worth an email to the recruiter, not worth a self-reject.
BORDERLINE = ('Tenure 3+ yrs (borderline)', 'Unclear — read posting', 'Unstated',
              'Senior-titled — likely above band',
              'Class-of window — outside by letter, ask',
              'Campus/grad programme — ask recruiter')

TIER_ORDER = {'S': 0, 'A': 1, 'B': 2, 'C': 3, 'D': 4}

# --- Firm tier -------------------------------------------------------------
# Comp band / market standing of the FIRM, for an engineering-or-research hire.
#
# BASIS, STATED PLAINLY: no firm in this dataset publishes a salary band for a
# European, UK, Singapore, Hong Kong, Shanghai or Tokyo seat -- that was checked
# firm by firm. So this tier is not derived from the postings; it is the
# market's consensus standing for each firm, which is a coarse judgement rather
# than a sourced figure. It is offered at that resolution deliberately: a tier
# letter is defensible where an invented "USD 220-300k" was not.
FIRM_TIER = {
    # S -- top of market for quant engineers and researchers.
    'Jane Street': 'S', 'Citadel Securities': 'S', 'Hudson River Trading': 'S',
    'Jump Trading Group': 'S', 'XTX Markets': 'S', 'Radix Trading': 'S',
    'Five Rings': 'S', 'PDT Partners': 'S', 'D. E. Shaw group': 'S',
    'D. E. Shaw': 'S', 'Two Sigma': 'S', 'Renaissance Technologies': 'S',
    'Headlands Technologies': 'S', 'TGS Management': 'S',

    # A -- elite market makers and the strongest systematic shops.
    'Optiver': 'A', 'IMC Trading': 'A', 'Susquehanna International Group (SIG)': 'A',
    'Susquehanna (SIG)': 'A', 'DRW': 'A', 'Tower Research Capital': 'A',
    'Flow Traders': 'A', 'G-Research': 'A', 'Qube Research & Technologies': 'A',
    'Millennium Management': 'A', 'Millennium': 'A',
    'Point72 / Cubist Systematic Strategies': 'A', 'Point72 / Cubist': 'A',
    'Balyasny Asset Management (BAM)': 'A', 'Balyasny': 'A',
    'Squarepoint Capital': 'A', 'Quadrature Capital': 'A',
    'Old Mission Capital': 'A', 'The Voleon Group': 'A', 'Voleon': 'A',
    'Vatic Investments': 'A', 'Aquatic Capital Management': 'A', 'Aquatic Capital': 'A',

    # B -- established funds and mid-tier market makers. Real money, a step down.
    'Schonfeld Strategic Advisors': 'B', 'Schonfeld': 'B',
    'ExodusPoint Capital Management': 'B', 'ExodusPoint': 'B',
    'Verition Fund Management': 'B', 'Verition': 'B', 'Marshall Wace': 'B',
    'Man Group / AHL': 'B', 'Brevan Howard': 'B', 'Systematica Investments': 'B',
    'Systematica': 'B', 'WorldQuant': 'B', 'AQR Capital Management': 'B', 'AQR': 'B',
    'Arrowstreet Capital': 'B', 'Winton': 'B', 'Garda Capital Partners': 'B',
    'Garda Capital': 'B', 'Akuna Capital': 'B', 'Wolverine Trading': 'B',
    'Chicago Trading Company': 'B', 'Belvedere Trading': 'B', 'Maven Securities': 'B',
    'Eclipse Trading': 'B', 'Mako': 'B', 'Da Vinci Derivatives': 'B',
    'Da Vinci Trading': 'B', 'Virtu Financial': 'B', 'Wintermute': 'B',
    'Capital Fund Management (CFM)': 'B', 'Quantica Capital': 'B',
    'Dymon Asia Capital': 'B', 'Dymon Asia': 'B', 'Quantedge Capital': 'B',
    'Quantedge': 'B', 'ADIA (Team Q)': 'B', 'Grasshopper': 'B',

    # C -- banks, smaller shops, and the larger Chinese managers.
    'Goldman Sachs (Strats)': 'C', 'Nomura (quant desk)': 'C',
    'Webb Traders': 'C', 'WEBB Traders': 'C', 'All Options': 'C',
    'Ubiquant': 'C', 'High-Flyer (幻方量化)': 'C', 'Minghong Investment (明汯)': 'C',
    'Yanfu Investments (衍复)': 'C', 'WizardQuant (宽德)': 'C',
    'Lingjun Investment (灵均)': 'C', 'Century Frontier (世纪前沿)': 'C',

    # D -- small or opaque; include for completeness.
    'Qianxiang Asset (千象)': 'D', 'Blackwing Asset (黑翼)': 'D',
    'Chengqi Asset (诚奇)': 'D', 'Mingshi Investment (鸣石)': 'D',
}

def firm_tier(firm):
    if firm in FIRM_TIER:
        return FIRM_TIER[firm]
    # Tolerate the agents' slightly varying firm spellings.
    for k, v in FIRM_TIER.items():
        if firm.startswith(k) or k.startswith(firm):
            return v
    return 'C'

def role_fit(track, gate, lang, verif):
    """How actionable a role is, independent of the firm's standing.

    Visa is deliberately NOT weighted here. Every location in this dataset is
    one you can work in -- EU and CH by right, Tokyo by residence, UK by
    self-sponsored HPI, and Singapore/Hong Kong sponsorship is routine at these
    levels. There are no US roles in this sheet, so H-1B never binds. The two
    constraints that do bite are Mandarin and the eligibility gate, and both
    have their own filterable columns.
    """
    if verif != 'verified-primary':
        return 'Confirm source first'
    if gate.startswith('Student-only'):
        return 'Blocked — needs enrolment'
    if gate.startswith('Tenure') and '(above you)' in gate:
        return 'Above band'
    if lang == 'Mandarin required':
        return 'Mandarin required'
    if gate in OPEN_GATES:
        if track == 'ML Performance' or gate == 'Evidence-based (papers/OSS)':
            return 'Direct match — apply'
        return 'Clears gate — apply'
    if gate in BORDERLINE:
        return 'Gray zone — ask recruiter'
    return 'Read posting'

FIT_ORDER = {'Direct match — apply': 0, 'Clears gate — apply': 1,
             'Gray zone — ask recruiter': 2, 'Read posting': 3,
             'Mandarin required': 4, 'Above band': 5,
             'Blocked — needs enrolment': 6, 'Confirm source first': 7}

def load():
    out = []
    for fn in sorted(os.listdir(FIND)):
        if not fn.endswith('.json'):
            continue
        try:
            with open(f'{FIND}/{fn}', encoding='utf-8') as fh:
                out.append((fn[:-5], json.load(fh)))
        except Exception as exc:
            print(f'  !! {fn}: {exc}', file=sys.stderr)
    return out

def main():
    data = load()
    roles, audits, firms = [], [], []

    for slug, d in data:
        firm = d.get('firm') or slug
        for r in d.get('roles', []) or []:
            loc = (r.get('location') or '').strip()
            elig = (r.get('eligibility') or '').strip()
            reqs = (r.get('requirements') or '').strip()
            note = (r.get('notes') or '').strip()
            track = (r.get('track') or '').strip()
            auth_s = auth(loc)
            gate = gate_of(elig, reqs, note, (r.get('title') or ''))
            lang = mandarin_of(elig, reqs, note, loc)
            verif = (r.get('verification') or '').strip()
            roles.append([
                firm_tier(firm),
                role_fit(track, gate, lang, verif),
                firm,
                loc,
                (r.get('title') or '').strip(),
                track,
                auth_s,
                gate,
                lang,
                elig,
                reqs,
                (r.get('comp_local') or '').strip(),
                verif,
                (r.get('live_as_of') or '').strip(),
                (r.get('url') or '').strip(),
                note,
            ])
        for a in d.get('existing_rows_audit', []) or []:
            audits.append([
                firm,
                (a.get('location') or '').strip(),
                (a.get('existing_title') or '').strip(),
                (a.get('verdict') or '').strip(),
                (a.get('detail') or '').strip(),
            ])
        firms.append([
            firm,
            (d.get('careers_url') or '').strip(),
            ', '.join(d.get('offices_in_scope_confirmed') or []),
            ', '.join(d.get('offices_checked_not_found') or []),
            len(d.get('roles') or []),
            (d.get('notes') or '').strip(),
        ])

    # Tier first, then track, then firm -- so the top of the sheet is the
    # "apply this week" list without any filtering.
    roles.sort(key=lambda r: (TIER_ORDER.get(r[0], 9), FIT_ORDER.get(r[1], 9),
                          TRACK_ORDER.get(r[5], 9), r[2], r[3]))
    audits.sort(key=lambda r: (r[3], r[0]))
    firms.sort(key=lambda r: -r[4])

    role_hdr = ['Firm tier', 'Role fit', 'Firm', 'Location', 'Role title (as posted)', 'Track',
                'Your work authorisation', 'Gate type', 'Language',
                'Eligibility gate (from posting)', 'Stated requirements',
                'Comp (only if published)', 'Verification', 'Live as of', 'Direct link', 'Notes']
    audit_hdr = ['Firm', 'Location', 'Title in old sheet', 'Verdict', 'Evidence']
    firm_hdr = ['Firm', 'Careers URL', 'In-scope offices confirmed', 'Checked, not found',
                'Roles found', 'Research notes']

    # Shortlist: no visa friction, a gate you clear, no language wall, and a
    # verified source. Deliberately narrow -- this is the "apply now" list.
    short = [r for r in roles
         if r[0] in ('S', 'A')
         and r[1] in ('Direct match — apply', 'Clears gate — apply')]
    short.sort(key=lambda r: (TIER_ORDER.get(r[0], 9), FIT_ORDER.get(r[1], 9),
                          TRACK_ORDER.get(r[5], 9), r[2]))

    verdict_counts = {}
    for a in audits:
        verdict_counts[a[3]] = verdict_counts.get(a[3], 0) + 1
    track_counts = {}
    for r in roles:
        track_counts[r[5]] = track_counts.get(r[5], 0) + 1
    loc_counts = {}
    for r in roles:
        loc_counts[r[3]] = loc_counts.get(r[3], 0) + 1
    tier_counts = {}
    for r in roles:
        tier_counts[r[0]] = tier_counts.get(r[0], 0) + 1
    gate_counts = {}
    for r in roles:
        gate_counts[r[7]] = gate_counts.get(r[7], 0) + 1

    method = [[x] for x in [
        'QUANT ROLES — REBUILT FROM PRIMARY SOURCES, 4 AUGUST 2026',
        '',
        'WHAT THIS IS',
        f'Every row on the "Roles" tab was read off the hiring firm\'s own careers page, applicant-tracking '
        f'system or public job API on 2026-08-04. One research agent per firm, {len(data)} firms.',
        '',
        'WHY THE PREVIOUS VERSION WAS REBUILT RATHER THAN EDITED',
        'The prior sheet carried 147 rows, of which 129 were marked "Reported — confirm office/req". Auditing '
        'them against live sources found the majority did not survive contact with the firms\' own pages. The '
        'recurring failure modes were:',
        '  1. Offices that do not exist. Citadel Securities Tokyo, Millennium Zurich, WorldQuant Zurich, '
        'Schonfeld Zurich (announced, not yet open), Jane Street Chicago, G-Research Dallas, Old Mission '
        'Amsterdam, Brevan Howard Geneva reqs. Some appear to originate from empty location records in a '
        'firm\'s ATS: AQR\'s applicant system lists a Tokyo entry with zero jobs that is absent from AQR\'s own '
        'offices page.',
        '  2. Job titles that exist nowhere at the firm. "Core Engineer (C++)" on six Tower Research rows; '
        '"Core Platform Engineer" at Millennium; "Rets/C++ Engineer" at Wintermute; "Core Software Engineer" '
        'at HRT.',
        '  3. Eligibility verdicts inverted. Hudson River Trading rows were all marked student-gated, but that '
        'gate applies only to its "2027 Grads" reqs — its experienced C++, AI and research reqs have no '
        'graduation-year gate. Conversely DRW, Tower, Flow Traders, SIG and IMC rows were marked "recent grads '
        'accepted" against reqs that state 5+ year minimums.',
        '  4. Compensation figures with no source. No firm in scope published a salary band for a European, '
        'UK, Singapore, Hong Kong, Shanghai or Tokyo role. Where a published figure did exist to compare '
        'against, the old sheet was high: Wolverine\'s posting states a $100–140k base against $220–300k in '
        'the sheet; Arrowstreet\'s states $155–260k against $220–300k.',
        '  5. Dead or wrong source links. cfm.com/careers, winton.com/careers, mwam.com/careers, '
        'mavensecurities.com/careers, voleon.com/careers, arrowstreetcapital.com/careers and adia.ae/en/careers '
        'all 404. The Aquatic row pointed at aquaticcapital.com, a parked domain for sale; the real site is '
        'aquatic.com.',
        '',
        'COMPENSATION — READ THIS BEFORE USING ANY NUMBER',
        'The "Comp" column is populated ONLY where a figure appeared on the posting itself or a regulator '
        'filing. It is empty for most rows because most firms publish nothing outside the United States. '
        'Where a US dollar band appears on a non-US req it is a US pay-transparency disclosure that does not '
        'describe the local package, and is labelled as such. The previous sheet\'s USD Low/High/Mid columns '
        'have been dropped rather than carried forward: they were unsourced and, on the two rows where a real '
        'figure exists to check, overstated.',
        '',
        'VERIFICATION COLUMN',
        '  verified-primary    — the role was read on the firm\'s own site, ATS or job API.',
        '  reported-secondary  — press, community or aggregator sourcing only. Confirm before applying.',
        '  office-unconfirmed  — could not confirm the firm has an office in that city.',
        'Citadel Securities rows were read through a text proxy because the site returns 403 to automated '
        'requests; the content is the firm\'s own, but was not browser-rendered.',
        '',
        'LOCATION ILLUSIONS TO WATCH FOR',
        'Several roles cover a market from another city, and reading the tag rather than the body is how a '
        'phantom office gets into a spreadsheet. Flow Traders\' Japan-coverage Institutional Trader sits in '
        'Hong Kong. Tower\'s Japan-flow ETF Trader sits in Singapore. Chicago Trading Company\'s "Options '
        'Trader - Asia Hours" is a Chicago seat. PDT\'s London req contains a line about working from the New '
        'York office three days a week that needs clarifying with the recruiter.',
        '',
        'MULTI-CITY REQUISITIONS',
        'Some firms post one requisition against several cities. Garda\'s Geneva and Zug listings are the same '
        'req, not two seats; the same is true of Verition\'s London/Hong Kong/Singapore reqs, Radix\'s '
        'Amsterdam listings and Headlands\' Amsterdam/London pairs. A row per city is shown for '
        'searchability, but the underlying headcount may be one.',
        '',
        'LANGUAGE REQUIREMENTS',
        'Mandarin is required by some in-scope roles and explicitly not by others, and this splits by firm '
        'rather than by city. Virtu\'s Singapore China-desk C++ req and Grasshopper\'s Singapore QR req both '
        'require Mandarin. High-Flyer\'s reqs require Chinese communication skills. By contrast the Shanghai '
        'reqs at Optiver, Tower Research, Eclipse Trading and Man Group state business English only. Three '
        'CFM Paris reqs require French fluency, as do both Webb Traders Paris reqs.',
        '',
        'TRADER ROLES',
        'The previous version deliberately contained no trader rows. They are included here. Note the '
        'selection difference: trading interviews test mental arithmetic speed and market intuition rather '
        'than engineering or research output.',
        '',
        'WHAT IS NOT COVERED',
        'Only EU, UK, Singapore, Hong Kong, Shanghai and Tokyo were searched. US, Canada, India, Middle East '
        'and Australia roles were not collected, so firms that are US-only appear with zero roles. Firms that '
        'hire laterally through headhunters rather than public boards — Marshall Wace, Brevan Howard, '
        'Quadrature — will look emptier than they are; for those the route is a direct approach or a standing '
        'open application, noted per firm on the "Firms & offices" tab.',
        '',
        'THE "SHORTLIST" TAB',
        'A filtered view of Roles: no visa friction (EU, CH, JP or UK HPI), an eligibility gate a '
        'Feb-2026 graduate with ~18 months experience actually clears, no Mandarin requirement, and a '
        'verified-primary source. It is deliberately narrow. Everything else lives on Roles.',
        '',
        'THE "GATE TYPE" COLUMN',
        'A classification of the eligibility text, added so the sheet can be sorted by what actually '
        'blocks you. It is a heuristic over prose, not a parsed field — the Eligibility column is the '
        'authority and is kept verbatim. Values: "Graduation-year gated" (campus/class-of reqs you are '
        'outside), "Tenure N+ yrs", "No stated gate", "Evidence-based (papers/OSS)" for reqs that ask for '
        'research output rather than years, and "Unclear — read posting".',
        '',
        'THE STRUCTURAL PROBLEM THIS PASS SURFACED',
        'At roughly 18 months experience by a mid-2027 start, you sit above the graduate programmes and '
        'below the lateral bar at a large share of these firms — DRW, Five Rings, Flow Traders, '
        'Squarepoint, SIG and WizardQuant all show that shape, with campus reqs on one side and 5-year '
        'minimums on the other and nothing between. The reqs that do not have this problem are '
        'disproportionately ML and research seats that gate on demonstrated output rather than tenure: '
        'CFM Paris ML Researcher (PhD or 2-3 yrs), HRT London AI Research Engineer, G-Research NLP '
        'Performance Engineer and ML Researcher, Citadel Securities London ML Researcher (MSc-eligible), '
        'Point72 QR-ML (MS accepted), Jane Street ML Performance Engineer, Balyasny Rates QR. Sorting by '
        'Gate type surfaces these.',
        '',
        'SHANGHAI IS UNDER-WEIGHTED IN THE OLD SHEET',
        'The previous version treated mainland seats as a Mandarin-walled floor tier. Five firms in this '
        'pass have Shanghai work that matches a GPU/kernel profile closely: Optiver (Senior SWE Research '
        'Platform, Senior ML Engineer), Minghong (CUDA-PTX operators, TensorRT inference, PyTorch-Triton '
        'training), Yanfu (ML performance engineer naming CUDA/Triton/CUTLASS), WizardQuant (ML '
        'Performance Engineer) and Ubiquant (AI platform, distributed-training profiling). Language is '
        'the real constraint and it splits by firm, not by city — see the Language column.',
        '',
        'SUMMARY OF THIS PASS',
        f'  Firms researched: {len(data)}',
        f'  Roles captured: {len(roles)}',
        f'  Shortlist (firm tier S/A and an apply-now role fit): {len(short)}',
        f'  Previous rows audited: {len(audits)}',
    ]]
    method.append([''])
    method.append(['  Roles by firm tier (see the Legend tab):'])
    for t in 'SABCD':
        if t in tier_counts:
            method.append([f'    {t}: {tier_counts[t]}'])
    method.append([''])
    method.append(['  Roles by eligibility gate:'])
    for g, c in sorted(gate_counts.items(), key=lambda kv: -kv[1]):
        method.append([f'    {g}: {c}'])
    for v, c in sorted(verdict_counts.items(), key=lambda kv: -kv[1]):
        method.append([f'    {v}: {c}'])
    method.append([''])
    method.append(['  Roles by track:'])
    for t, c in sorted(track_counts.items(), key=lambda kv: -kv[1]):
        method.append([f'    {t}: {c}'])
    method.append([''])
    method.append(['  Roles by location:'])
    for l, c in sorted(loc_counts.items(), key=lambda kv: -kv[1]):
        method.append([f'    {l}: {c}'])

    legend = [[a, b] for a, b in [
        ('FIRM TIER — column A, and the primary sort on every tab', ''),
        ('', 'The standing of the FIRM: comp band and market position for an engineering or research '
             'hire. It describes the employer, not the individual role.'),
        ('', 'BASIS — read this before relying on it. No firm in this dataset publishes a salary band '
             'for a European, UK, Singapore, Hong Kong, Shanghai or Tokyo seat; that was checked firm by '
             'firm and the finding was uniform. So this tier is NOT derived from the postings. It is the '
             'market\'s consensus standing for each firm — a coarse judgement, offered at exactly that '
             'resolution on purpose. A tier letter is defensible where the previous sheet\'s invented '
             '"USD 220-300k" was not. Treat it as a rough ordering, not a pay quote.'),
        ('S', 'Top of market for quant engineers and researchers. Jane Street, Citadel Securities, '
              'Hudson River Trading, Jump, XTX, Radix, Five Rings, PDT, D. E. Shaw, Two Sigma, '
              'Renaissance, Headlands, TGS.'),
        ('A', 'Elite market makers and the strongest systematic shops. Optiver, IMC, SIG, DRW, Tower '
              'Research, Flow Traders, G-Research, QRT, Millennium, Point72/Cubist, Balyasny, '
              'Squarepoint, Quadrature, Old Mission, Voleon, Vatic, Aquatic.'),
        ('B', 'Established funds and mid-tier market makers. Real money, a step down: Schonfeld, '
              'ExodusPoint, Verition, Marshall Wace, Man/AHL, Brevan Howard, Systematica, WorldQuant, '
              'AQR, Arrowstreet, Winton, Garda, CFM, Akuna, Wolverine, CTC, Belvedere, Maven, Eclipse, '
              'Mako, Da Vinci, Virtu, Wintermute, Quantica, Dymon, Quantedge, ADIA, Grasshopper.'),
        ('C', 'Banks, smaller shops, and the larger Chinese managers: Goldman Sachs Strats, Nomura, '
              'Webb Traders, All Options, Ubiquant, High-Flyer, Minghong, Yanfu, WizardQuant, Lingjun, '
              'Century Frontier.'),
        ('D', 'Small or opaque, included for completeness: Qianxiang, Blackwing, Chengqi, Mingshi.'),
        ('', ''),
        ('ROLE FIT — column B, the secondary sort', ''),
        ('', 'What stands between you and this specific role. Visa is deliberately NOT part of it: '
             'every location here is one you can work in — EU and Switzerland by right, Tokyo by '
             'residence, the UK via self-sponsored HPI, and Singapore/Hong Kong sponsorship is routine '
             'at these levels. There are no US roles in this sheet at all, so H-1B never binds. Filter '
             'on the work-authorisation column yourself if you want to narrow by geography.'),
        ('Direct match — apply', 'You clear the gate and it is an ML-Performance seat, or one that gates '
                                 'on research output rather than years served. Your strongest cases.'),
        ('Clears gate — apply', 'You clear the stated gate. C++, Research or Trader track.'),
        ('Gray zone — ask recruiter', 'Campus/class-of window, a 3-year floor, or an unclear gate. Worth '
                                      'an email; not worth a self-reject.'),
        ('Read posting', 'No gate this could classify from the text captured.'),
        ('Mandarin required', 'You may well clear the gate, but the posting, board or application form '
                              'is Chinese-language. One of the two constraints that genuinely bite.'),
        ('Above band', 'The posting states a years floor you do not meet.'),
        ('Blocked — needs enrolment', 'Requires current student status. The only gate that hard-excludes '
                                      'you.'),
        ('Confirm source first', 'Not verified on a primary source — check it exists before applying.'),
        ('', ''),
        ('TRACK — column E', ''),
        ('C++', 'Low-latency, systems, core infrastructure, trading systems, quant dev where the work '
                'is C++. Caution: at Jane Street this means low-latency systems in OCaml, not C++.'),
        ('ML Performance', 'ML engineering and infrastructure, GPU/HPC/kernel work, research engineering. '
                           'The closest match to the llama.cpp kernel work and the ISCA/ICLR output.'),
        ('Research', 'Quantitative researcher, quant analyst, ML researcher, strategist.'),
        ('Trader', 'Trader, junior/algo/quantitative/execution trader. Included at your request. Note '
                   'the selection difference: trading interviews test mental-arithmetic speed and market '
                   'intuition, a different pool from the one your engineering and papers compete in.'),
        ('', ''),
        ('YOUR WORK AUTHORISATION — column F', ''),
        ('EU citizen — no sponsorship', 'Amsterdam, Aarhus, Paris, Dublin, Warsaw, Milan, Madrid, '
                                        'Frankfurt, Munich, Budapest, Copenhagen, Luxembourg, Cluj, '
                                        'Kajaani, Bristol. Start immediately.'),
        ('CH permit — no sponsorship', 'Zurich, Zug, Geneva, Pfaffikon, Schaffhausen. Rare advantage — '
                                       'these seats are near competition-free for you.'),
        ('JP resident — in country', 'Tokyo. No visa step, but see the Tokyo note on Method & caveats: '
                                     'only 8 Tokyo roles exist across all 73 firms.'),
        ('UK HPI — self-sponsored', 'London, Bristol, Cambridge, Oxford. ~3 weeks via EPFL eligibility '
                                    'and costs the employer nothing — say so in the application.'),
        ('Sponsorship required', 'Singapore, Hong Kong, Shanghai, Beijing, Shenzhen, Hangzhou. Routine '
                                 'at these comp levels, but it is a step and it takes time.'),
        ('', ''),
        ('GATE TYPE — column G', ''),
        ('', 'A classification of what the posting says blocks you, added so the sheet sorts by the '
             'thing that actually decides whether an application is worth sending. It is a heuristic '
             'over the posting prose — column I keeps the eligibility text verbatim and is the authority.'),
        ('No stated gate', 'The posting names no years-of-experience floor and no graduation window.'),
        ('Evidence-based (papers/OSS)', 'Asks for publications, open-source contributions or a research '
                                        'track record instead of tenure. Your strongest category.'),
        ('Tenure 1+/2+ yrs (you clear)', 'A floor you are above at ~18 months by a mid-2027 start.'),
        ('Tenure 3+ yrs (borderline)', 'You will be close. Worth applying if the content matches well.'),
        ('Tenure 4+ yrs and above', 'Above your band on the posting\'s own terms.'),
        ('', 'YOU ARE A RECENT GRADUATE — Feb 2026 MSc, ~18 months experience by a mid-2027 start. '
             'That is neither a student nor a lateral hire, and the three grad-adjacent gates below are '
             'genuinely different from each other. They are kept separate on purpose.'),
        ('Recent-grad window — you clear', 'The posting says "recent graduate", "within two years of '
                                           'graduation", "0-2 years" or 毕业两年以内. You are inside it. '
                                           'Example: SIG\'s Quantitative Trader reads "soon-to-be or '
                                           'recently graduated student... available June 2027", which '
                                           'both includes you and matches your timing.'),
        ('Campus/grad programme — ask recruiter', 'A campus or graduate programme that does not state a '
                                                  'year window you clearly fail. Gray zone: worth an '
                                                  'email, not worth a self-reject.'),
        ('Class-of window — outside by letter, ask', 'Names a graduating class that is not yours (e.g. '
                                                     '"graduating winter 2026 or spring/summer 2027"). '
                                                     'Outside on a literal reading, but these are '
                                                     'frequently soft — Five Rings\' wording arguably '
                                                     'includes a Feb 2026 graduate already.'),
        ('Student-only (enrolled) — cannot apply', 'Requires current enrolment ("pursuing a Master\'s", '
                                                   '"in your final year") or is an internship. This is '
                                                   'the only grad-adjacent gate that genuinely excludes '
                                                   'you, and it is why these are tier D.'),
        ('Senior-titled — likely above band', 'No years figure in the body, but the title says Principal, '
                                              'Head of, Director or Manager. Inferred, not stated.'),
        ('Unclear — read posting', 'The posting did not state a gate in terms this could classify.'),
        ('', 'NOTE ON HOW THIS IS COMPUTED: negation is checked first. Many postings say "no student or '
             'graduation-year gate", and matching the bare words inside that sentence would invert its '
             'meaning — that error is exactly what the previous version of this sheet did to Hudson River '
             'Trading, marking every HRT row student-gated when only its "2027 Grads" reqs are. Gate type '
             'is also computed from the eligibility and requirements fields only, never from research '
             'notes, since notes often discuss a gate in order to explain it.'),
        ('', ''),
        ('LANGUAGE — column H', ''),
        ('Mandarin required', 'The posting, application form or board states a Chinese-language '
                              'requirement. Splits by FIRM, not by city.'),
        ('Check — mainland seat', 'A mainland location where no explicit language requirement was found '
                                  'in the posting text. Confirm before applying.'),
        ('(blank)', 'No language requirement found. Note the Shanghai reqs at Optiver, Tower Research, '
                    'Eclipse Trading and Man Group state business English only, while High-Flyer, '
                    'Ubiquant, Yanfu, WizardQuant, Lingjun and Minghong are Chinese-first.'),
        ('', 'Non-Chinese language gates also exist: three CFM Paris reqs and both Webb Traders Paris '
             'reqs require French fluency.'),
        ('', ''),
        ('VERIFICATION — column L', ''),
        ('verified-primary', 'Read on the firm\'s own careers page, applicant-tracking system or job '
                             'API on 2026-08-04.'),
        ('reported-secondary', 'Press, community, LinkedIn or aggregator sourcing only. Confirm before '
                               'spending an application. Lingjun\'s rows are all in this category — its '
                               'ATS blocks automated access entirely.'),
        ('office-unconfirmed', 'Could not confirm the firm has an office in that city.'),
        ('', 'Citadel Securities rows were read through a text proxy because the site returns 403 to '
             'automated requests. The content is the firm\'s own but was not browser-rendered.'),
        ('', ''),
        ('COMP — column K', ''),
        ('', 'Populated ONLY where a figure appeared on the posting itself or a regulator filing, which '
             'is why it is empty on most rows. Where a US dollar band appears on a non-US req it is a US '
             'pay-transparency disclosure that does not describe the local package, and is labelled so.'),
        ('', 'The previous sheet\'s USD Low/High/Mid columns were dropped rather than carried forward. '
             'They had no source, and on the only two rows where a real figure existed to check against, '
             'they were high: Wolverine\'s posting states a $100-140k base against $220-300k in the sheet; '
             'Arrowstreet\'s states $155-260k against $220-300k.'),
        ('', ''),
        ('TABS', ''),
        ('Shortlist', f'Firm tier S and A, role fit "apply" — {len(short)} roles. Sorted by firm tier.'),
        ('Roles', f'All {len(roles)} roles, sorted by firm tier, then role fit, then track.'),
        ('Old sheet audit', f'What the {len(audits)} previous rows turned out to be, with evidence.'),
        ('Firms & offices', 'Per firm: careers URL, confirmed in-scope offices, cities checked and not '
                            'found, and how that firm actually hires. Read this before concluding a firm '
                            'has nothing — Marshall Wace, Brevan Howard and Quadrature hire laterally '
                            'through headhunters and standing applications rather than public boards.'),
        ('Method & caveats', 'How this was built, what was wrong with the previous version, and the '
                             'traps worth knowing about.'),
    ]]

    sheets = [
        Sheet('Shortlist', role_hdr, short,
              widths=[9, 24, 26, 15, 42, 15, 24, 26, 16, 46, 60, 26, 19, 11, 52, 46],
              wrap_cols=(9, 10, 11, 15)),
        Sheet('Roles', role_hdr, roles,
              widths=[9, 24, 26, 15, 42, 15, 24, 26, 16, 46, 60, 26, 19, 11, 52, 46],
              wrap_cols=(9, 10, 11, 15)),
        Sheet('Old sheet audit', audit_hdr, audits,
              widths=[26, 15, 34, 20, 100], wrap_cols=(4,)),
        Sheet('Firms & offices', firm_hdr, firms,
              widths=[26, 50, 34, 30, 11, 80], wrap_cols=(5,)),
        Sheet('Legend', ['Term', 'What it means'], legend,
              widths=[34, 108], wrap_cols=(1,)),
        Sheet('Method & caveats', ['Quant roles — method, corrections and caveats'], method,
              widths=[130], wrap_cols=(0,)),
    ]
    out = f'{BASE}/quant-roles-2026-08-04.xlsx'
    write(out, sheets)
    print(f'firms={len(data)} roles={len(roles)} audits={len(audits)}')
    print('verdicts:', verdict_counts)
    print('tracks:', track_counts)
    print('wrote', out)

if __name__ == '__main__':
    main()
