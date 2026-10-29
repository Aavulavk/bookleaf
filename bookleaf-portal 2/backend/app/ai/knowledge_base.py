"""BookLeaf knowledge base, split into sections so each draft only carries the
sections relevant to the ticket category (cost control)."""

TONE = """\
- Always empathetic and professional. Authors are partners, not customers to be managed.
- Acknowledge the author's concern before jumping to solutions.
- Be specific: use actual numbers, dates and statuses instead of vague reassurance.
- If something is BookLeaf's fault (delayed royalty, ISBN error), own it directly. No corporate deflection.
- If it needs escalation or investigation, give a clear timeline (e.g. "within 48 hours"), never open-ended promises.
- Always end with a clear next step for the author and/or the BookLeaf team."""

SECTIONS = {
    "company": """\
BookLeaf Publishing is a self-publishing company in India and the US. Packages: Standard Free (no upfront cost) and Bestseller Breakthrough (paid, with marketing and distribution add-ons). We handle cover design, typesetting, ISBN assignment, printing, distribution and royalty management. In-house printing facility and warehouse are in Delhi; print partners are Repro India and Epitome Books.""",
    "royalty": """\
ROYALTY POLICY: 80/20 split of net profit (80% author, 20% BookLeaf). Net profit = MRP minus printing cost, platform commission (Amazon/Flipkart) and shipping charges. Royalties are calculated quarterly and paid within 45 days of the quarter ending. Minimum payout threshold is Rs 1,000; smaller balances roll over to the next quarter. Payouts are by bank transfer to the account linked in the author's dashboard. Authors can see a royalty breakdown with per-platform sales in their dashboard. We can share a detailed line-by-line breakdown on request.""",
    "isbn": """\
ISBN POLICY: Every book gets a unique ISBN assigned by BookLeaf, registered under BookLeaf's publisher imprint. An author who wants an ISBN under their own imprint must obtain it independently. ISBN errors (duplicate, wrong book linked, mismatch between platform and physical copy) are high-priority and escalated to the production team.""",
    "printing": """\
PRINTING & QUALITY: In-house printing handles most orders; overflow or special formats go to Repro India or Epitome Books. Standard print turnaround is 5-7 business days from order confirmation. For quality issues (misprints, binding defects, colour inconsistency) BookLeaf arranges a free reprint after verification; the author may need to share photos of the defective copy.""",
    "distribution": """\
DISTRIBUTION: Books are listed on Amazon India, Flipkart, Amazon US, Amazon UK and the BookLeaf Store. New listings go live 7-10 business days after publication is complete. A book showing as unavailable on a platform usually means a stock sync issue; the team can trigger a re-sync, which takes 24-48 hours. Metadata updates (e.g. description) can be submitted via the dashboard or by emailing the team and typically reflect on platforms in 3-5 business days.""",
    "production": """\
PRODUCTION STAGES: Manuscript Received -> Editing (if opted) -> Cover Design -> Typesetting -> Proofreading -> ISBN Assignment -> Printing -> Distribution Setup -> Published & Live. Authors are emailed at each stage. Delays usually happen at Cover Design (waiting for author approval) and Proofreading (revision rounds). Never blame the author for delays; frame it collaboratively.""",
}

# Which sections to include per category (company overview is always included).
CATEGORY_SECTIONS = {
    "Royalty & Payments": ["royalty"],
    "ISBN & Metadata Issues": ["isbn", "distribution"],
    "Printing & Quality": ["printing"],
    "Distribution & Availability": ["distribution"],
    "Book Status & Production Updates": ["production", "distribution"],
    "General Inquiry": ["distribution", "royalty"],
}


def kb_for_category(category: str) -> str:
    keys = ["company"] + CATEGORY_SECTIONS.get(category, ["distribution"])
    return "\n\n".join(SECTIONS[k] for k in keys)
