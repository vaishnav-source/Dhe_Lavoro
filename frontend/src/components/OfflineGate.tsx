import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import useOnlineStatus from "../hooks/useOnlineStatus";

// Shows a full-page "you're offline" screen while the connection is down,
// and reloads the page 1 second after the connection returns. Filters and
// page live in the URL, so nothing is lost.
export default function OfflineGate({ children }: { children: ReactNode }) {
  const { online, recheck } = useOnlineStatus();
  const [stillOffline, setStillOffline] = useState(false);

  // When the connection comes back after being down, reload the page.
  const wasOffline = useRef(false);

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | undefined;
    if (!online) {
      wasOffline.current = true;
    } else if (wasOffline.current) {
      timer = setTimeout(() => {
        // Reload only once the site is really reachable again.
        fetch("/", { cache: "no-store" })
          .then(() => window.location.reload())
          .catch(() => {});
      }, 1000);
    }
    return () => clearTimeout(timer);
  }, [online]);

  if (online) return <>{children}</>;

  const handleRetry = () => {
    setStillOffline(!recheck());
  };

  return (
    <div
      role="alert"
      className="min-h-screen bg-ink text-stock flex items-center justify-center px-6"
    >
      <div className="max-w-md text-center">
        <svg
          className="mx-auto mb-6 w-14 h-14 text-stock/60 animate-offline"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          {/* Outer arcs – fade in sequence */}
          <path
            className="offline-arc offline-arc-1"
            d="M2 8.8a15 15 0 0 1 4.2-2.6M22 8.8a15 15 0 0 0-10-3.3"
          />
          <path
            className="offline-arc offline-arc-2"
            d="M5 12.9a10 10 0 0 1 3.4-2M19 12.9a10 10 0 0 0-5.4-2.7"
          />
          <path
            className="offline-arc offline-arc-3"
            d="M8.5 16.4a5 5 0 0 1 7 0"
          />
          {/* Dot */}
          <path d="M12 20h.01" />
          {/* Slash – draws in */}
          <path className="offline-slash" d="M3 3l18 18" />
        </svg>

        <h1 className="font-['SF_Pro_Display'] font-semibold text-2xl">
          You're offline
        </h1>
        <p className="mt-3 text-sm text-stock/60">
          Check your internet connection. The page reloads by itself as soon as
          you're back online.
        </p>
        <button
          type="button"
          onClick={handleRetry}
          className="mt-8 px-5 py-2 rounded-lg border border-stock/30 font-mono text-sm hover:bg-stock/10 transition-colors"
        >
          Try again
        </button>
        <p className="mt-4 font-mono text-xs text-stock/40">
          {stillOffline ? "still no connection…" : "waiting for connection…"}
        </p>
      </div>

      {/* Animation styles */}
      <style>{`
        @keyframes offline-pulse {
          0%, 100% { opacity: 0.55; transform: scale(1); }
          50%      { opacity: 0.9;  transform: scale(1.04); }
        }

        @keyframes offline-arc {
          0%, 100% { opacity: 0.25; }
          40%      { opacity: 0.7; }
          70%      { opacity: 0.35; }
        }

        @keyframes offline-slash {
          0%   { stroke-dashoffset: 26; opacity: 0.4; }
          40%  { stroke-dashoffset: 0;  opacity: 1; }
          100% { stroke-dashoffset: 0;  opacity: 0.85; }
        }

        .animate-offline {
          animation: offline-pulse 2.4s ease-in-out infinite;
        }

        .offline-arc {
          animation: offline-arc 2.4s ease-in-out infinite;
        }
        .offline-arc-1 { animation-delay: 0s; }
        .offline-arc-2 { animation-delay: 0.15s; }
        .offline-arc-3 { animation-delay: 0.3s; }

        .offline-slash {
          stroke-dasharray: 26;
          stroke-dashoffset: 26;
          animation: offline-slash 2.4s ease-in-out infinite;
        }
      `}</style>
    </div>
  );
}