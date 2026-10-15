import { Link } from "react-router-dom";

interface Section {
  heading: string;
  body: React.ReactNode;
}

const SECTIONS: Section[] = [
  {
    heading: "What this site is",
    body: (
      <>
        This is an independent, personal project that aggregates publicly
        posted job listings from Infopark and Technopark's own websites into
        one searchable list. It is <strong>not affiliated with, endorsed by,
        or operated by</strong> Infopark, Technopark, or any company whose
        listing appears here. It is not a recruitment agency and does not
        act on behalf of any employer or candidate.
      </>
    ),
  },
  {
    heading: "Listings are copied, not verified",
    body: (
      <>
        Job titles, descriptions, experience ranges, closing dates, and
        contact details shown here are pulled automatically from the
        original source page. Nothing is manually checked, and a listing can
        be outdated, already closed, edited, or removed on the source site
        without this site reflecting that change immediately. The "experience"
        shown on a job card is an automated best-effort estimate extracted
        from the posting text — it can be missing, wrong, or misleading, and
        should never be treated as an authoritative requirement.
      </>
    ),
  },
  {
    heading: "Always check the original posting before you apply",
    body: (
      <>
        Before applying to anything, open the "Original Post" link on the
        job page and read the actual listing on Infopark's or Technopark's
        site. Confirm the role, requirements, experience level, and contact
        details there — not just what's summarized here. This site's job is
        to help you find something worth looking at, not to be the final
        word on what a role actually requires.
      </>
    ),
  },
  {
    heading: "Match your own skills — no guarantee of outcome",
    body: (
      <>
        Nothing on this site is a promise of an interview, a response, or a
        job offer. Whether you hear back or "crack" a role depends entirely
        on you, the employer, and factors this site has no visibility into
        or control over. Please only apply to roles where you genuinely meet
        (or are close to) the stated requirements — misrepresenting your
        experience wastes both your time and the employer's.
      </>
    ),
  },
  {
    heading: "Applying is between you and the employer",
    body: (
      <>
        Any application, email, or message you send using the contact
        details shown here goes directly to the company or its listed
        contact — this site is not a party to that communication, does not
        forward, screen, or store applications, and has no role in any
        hiring decision, offer, interview process, or dispute that follows.
      </>
    ),
  },
  {
    heading: "External links",
    body: (
      <>
        This site links out to Infopark, Technopark, and individual
        companies' own pages and inboxes. Once you leave this site, its
        content, accuracy, and privacy practices are entirely outside our
        control.
      </>
    ),
  },
  {
    heading: "No warranty",
    body: (
      <>
        This site is provided "as is," with no guarantee that listings are
        accurate, complete, current, or available without interruption. Use
        it at your own discretion, and treat it as a starting point for your
        job search rather than a source of truth.
      </>
    ),
  },
  {
    heading: "Changes to this page",
    body: (
      <>
        This page may be updated as the site changes. Continued use after an
        update means you accept the current version.
      </>
    ),
  },
];

const BROWSE_LINKS = [
  { label: "All Parks", to: "/" },
  { label: "Infopark Jobs", to: "/?source=infopark" },
  { label: "Technopark Jobs", to: "/?source=technopark" },
];

const COMPANY_LINKS = [{ label: "Terms & Conditions", to: "/terms" }];

const OFFICIAL_LINKS = [
  { label: "Infopark.in", href: "https://infopark.in" },
  { label: "Technopark.in", href: "https://technopark.in" },
];

export default function TermsPage() {
  return (
    <div className="min-h-screen overflow-x-hidden">
      <header className="bg-ink text-stock">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 pt-10 pb-8">
          <Link
            to="/"
            className="font-mono text-xs uppercase tracking-wider text-stock/60 hover:text-stock transition-colors"
          >
            ← back to jobs
          </Link>
          <h1 className="mt-4 font-display font-semibold text-3xl sm:text-4xl leading-tight">
            Terms &amp; Conditions
          </h1>
          <p className="mt-3 text-stock/60 text-sm font-body max-w-xl">
            Please read this before using the site or applying to anything
            listed here.
          </p>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 sm:px-6 py-10">
        <div className="rounded-xl border border-hairline bg-surface divide-y divide-hairline overflow-hidden">
          {SECTIONS.map((section) => (
            <div key={section.heading} className="p-6 sm:p-7">
              <h2 className="font-display font-semibold text-base text-inktext mb-2">
                {section.heading}
              </h2>
              <p className="text-sm text-inktext/70 leading-relaxed">
                {section.body}
              </p>
            </div>
          ))}
        </div>

        <p className="mt-6 text-center font-mono text-xs text-inktext/40">
          By using this site, you agree to the above.
        </p>
      </main>

     {/* ===== Footer ===== */}
           <footer className="mt-16 bg-ink text-stock w-screen relative left-1/2 -translate-x-1/2">
             <div className="max-w-5xl mx-auto px-4 sm:px-6 pt-12 pb-8">
               <div className="pb-10 border-b border-stock/10">
                 <div>
                   <span className="font-['SF_Pro_Display'] font-semibold text-xl">Dhe Lavoro</span>
                 </div>
                 <p className="mt-2 text-sm text-stock/50 max-w-sm">
                   Every open pass across Kerala's IT parks, aggregated from
                   Infopark and Technopark's own listings.
                 </p>
               </div>
     
               <div className="grid grid-cols-2 sm:grid-cols-3 gap-8 py-10">
                 <div>
                   <h3 className="font-mono text-xs uppercase tracking-wider text-stock/40 mb-3">
                     Browse
                   </h3>
                   <ul className="space-y-2 text-sm">
                     {BROWSE_LINKS.map((l) => (
                       <li key={l.label}>
                         <Link
                           to={l.to}
                           className="text-stock/70 hover:text-stock transition-colors"
                         >
                           {l.label}
                         </Link>
                       </li>
                     ))}
                   </ul>
                 </div>
     
                 <div>
                   <h3 className="font-mono text-xs uppercase tracking-wider text-stock/40 mb-3">
                     Company
                   </h3>
                   <ul className="space-y-2 text-sm">
                     {COMPANY_LINKS.map((l) => (
                       <li key={l.label}>
                         <Link
                           to={l.to}
                           className="text-stock/70 hover:text-stock transition-colors"
                         >
                           {l.label}
                         </Link>
                       </li>
                     ))}
                   </ul>
                 </div>
     
                 <div>
                   <h3 className="font-mono text-xs uppercase tracking-wider text-stock/40 mb-3">
                     Official Sites
                   </h3>
                   <ul className="space-y-2 text-sm">
                     {OFFICIAL_LINKS.map((l) => (
                       <li key={l.label}>
                         <a
                           href={l.href}
                           target="_blank"
                           rel="noopener noreferrer"
                           className="text-stock/70 hover:text-stock transition-colors"
                         >
                           {l.label}
                         </a>
                       </li>
                     ))}
                   </ul>
                 </div>
               </div>
     
               <div className="pt-6 border-t border-stock/10 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-stock/40">
                 <p>
                   © {new Date().getFullYear()} Dhe Lavoro. Not affiliated with
                   Infopark or Technopark.
                 </p>
                 <p>Job data sourced from Infopark and Technopark's public listings.</p>
               </div>
             </div>
           </footer>
         </div>
       );
     }