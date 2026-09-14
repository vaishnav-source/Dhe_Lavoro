import { useEffect, useState } from "react";
import type { ReactNode } from "react";

// Bump this if the terms meaningfully change — a new value means everyone
// sees the popup again, even people who already agreed to an older
// version, rather than silently carrying forward consent to text they
// never actually saw.
const STORAGE_KEY = "terms_accepted_v1";

export default function TermsGate({ children }: { children: ReactNode }) {
  // Starts "true" (gate hidden) on purpose — real state loads from
  // localStorage a tick later. Defaulting to "not yet decided" would
  // flash the modal open-then-closed on every repeat visit; this way a
  // returning visitor who already agreed sees nothing at all.
  const [accepted, setAccepted] = useState(true);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    setAccepted(localStorage.getItem(STORAGE_KEY) === "true");
  }, []);

  // Prevent the page underneath from scrolling while the modal is open —
  // the overlay blocks clicks already, but without this, touch/wheel
  // scroll events still pass through to the body behind it.
  useEffect(() => {
    if (accepted) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [accepted]);

  const handleContinue = () => {
    localStorage.setItem(STORAGE_KEY, "true");
    setAccepted(true);
  };

  return (
    <>
      {children}

      {!accepted && (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center bg-ink/80 backdrop-blur-sm px-4 py-8"
          role="dialog"
          aria-modal="true"
          aria-labelledby="terms-gate-heading"
        >
          <div className="w-full max-w-lg rounded-xl border border-hairline bg-surface shadow-xl overflow-hidden">
            <div className="bg-ink text-stock px-6 py-4">
              <span className="font-mono text-xs uppercase tracking-wider text-stock/60">
                before you continue
              </span>
              <h2
                id="terms-gate-heading"
                className="mt-1 font-display font-semibold text-xl"
              >
                Quick heads-up
              </h2>
            </div>

            <div className="p-6 max-h-[50vh] overflow-y-auto space-y-3 text-sm text-inktext/70 leading-relaxed">
              <p>
                This site aggregates public job listings from Infopark and
                Technopark — it isn't affiliated with either park or any
                listed employer, and it isn't a recruiter.
              </p>
              <p>
                Listings are pulled automatically and can be outdated,
                incorrect, or already closed. Always check the{" "}
                <strong>original posting</strong> before applying.
              </p>
              <p>
                Experience ranges shown are automated estimates, not
                guarantees — please only apply to roles that genuinely match
                your skills. There's no guarantee of a response or outcome.
              </p>
              <p>
                Read the full{" "}
                <a
                  href="/terms"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-park underline hover:no-underline"
                >
                  Terms &amp; Conditions
                </a>{" "}
                for details.
              </p>
            </div>

            <div className="px-6 pb-6">
              <label className="flex items-start gap-2.5 text-sm text-inktext cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={(e) => setChecked(e.target.checked)}
                  className="mt-0.5 w-4 h-4 accent-park shrink-0"
                />
                <span>I have read and agree to the Terms &amp; Conditions.</span>
              </label>

              <button
                onClick={handleContinue}
                disabled={!checked}
                className="mt-4 w-full rounded-lg bg-park text-white font-mono text-sm uppercase tracking-wide py-2.5 transition-colors hover:bg-park-dark disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:bg-park"
              >
                Agree &amp; Continue
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}