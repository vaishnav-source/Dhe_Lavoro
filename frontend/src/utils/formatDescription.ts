// Turns a raw scraped job-description blob into loosely structured
// sections for display. The scraper strips HTML entirely (see
// scraper/common/html_cleaner.py), so all formatting cues — headings,
// bullet lists — are gone by the time this text reaches the frontend.
// This is a best-effort heuristic reconstruction, not a real parser:
// every company writes postings differently (confirmed across both
// Infopark and Technopark samples), so it won't be perfect for every
// posting, but it turns the common patterns into something readable
// instead of one unbroken wall of text.

export interface DescriptionSection {
  heading: string | null;
  items: string[];
}

// Section header keywords seen repeatedly across real postings from both
// sources. Matched as whole phrases, case-insensitive, only when they
// appear to start a new section (i.e. as a standalone label, not buried
// mid-sentence) — see the word-boundary + immediate-capital-letter check
// in splitIntoSections.
const KNOWN_HEADERS = [
  "Brief Description",
  "About the Role",
  "Role Overview",
  "Key Responsibilities",
  "Main Responsibilities",
  "Responsibilities",
  "Required Skills",
  "Required Skills & Qualifications",
  "Requirements",
  "Preferred Skills",
  "Preferred Qualifications",
  "Qualifications",
  "Qualification",
  "Qualification & Experience",
  "Eligibility Criteria",
  "Key Skills",
  "Skills",
  "Technology Stack",
  "What We Offer",
  "Why Join Us",
  "What We're Looking For",
  "Application Details",
  "Compensation",
];

// Matches a short "Label:" style lead-in — the recurring pattern in many
// postings ("Backend: 7+ years of...", "Application Development: Design,
// develop..."). Used to split a run-on paragraph into bullet-like items.
const LABEL_ITEM_SPLIT = /(?=[A-Z][A-Za-z0-9 /&'-]{2,45}:\s)/g;

// Matches a leading bullet/number marker some postings already have
// (•, -, *, or "1.") once whitespace is collapsed by scraping.
const EXPLICIT_BULLET_SPLIT = /(?:^|\s)[•▪●\-*]\s+/g;

function splitIntoSections(text: string): DescriptionSection[] {
  const headerPattern = new RegExp(
    `(${KNOWN_HEADERS.map((h) => h.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})(?=[A-Z\\s:])`,
    "g"
  );

  const parts: { heading: string | null; body: string }[] = [];
  let lastIndex = 0;
  let lastHeading: string | null = null;
  let match: RegExpExecArray | null;

  while ((match = headerPattern.exec(text)) !== null) {
    const body = text.slice(lastIndex, match.index).trim();
    if (body) parts.push({ heading: lastHeading, body });
    lastHeading = match[1];
    lastIndex = match.index + match[1].length;
  }
  const tail = text.slice(lastIndex).trim();
  if (tail) parts.push({ heading: lastHeading, body: tail });

  if (parts.length === 0) {
    parts.push({ heading: null, body: text });
  }

  return parts.map(({ heading, body }) => ({
    heading,
    items: splitBodyIntoItems(body),
  }));
}

function splitBodyIntoItems(body: string): string[] {
  if (EXPLICIT_BULLET_SPLIT.test(body)) {
    return body
      .split(EXPLICIT_BULLET_SPLIT)
      .map((s) => s.trim())
      .filter(Boolean);
  }

  const labelSplit = body.split(LABEL_ITEM_SPLIT).map((s) => s.trim()).filter(Boolean);
  if (labelSplit.length >= 3) {
    return labelSplit;
  }

  // No detectable list structure — treat as prose. Still break into
  // sentences grouped in twos/threes so it isn't one giant paragraph.
  const sentences = body.match(/[^.!?]+[.!?]+(\s|$)/g)?.map((s) => s.trim()) ?? [body];
  const grouped: string[] = [];
  for (let i = 0; i < sentences.length; i += 2) {
    grouped.push(sentences.slice(i, i + 2).join(" "));
  }
  return grouped.length ? grouped : [body];
}

export function formatJobDescription(text: string): DescriptionSection[] {
  if (!text || !text.trim()) return [];
  return splitIntoSections(text.trim());
}