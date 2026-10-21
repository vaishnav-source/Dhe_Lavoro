import { useCallback, useEffect, useState } from "react";

// Tracks the browser's online/offline state. `recheck` re-reads
// navigator.onLine on demand (used by the "Try again" button in case an
// event was missed).
export default function useOnlineStatus() {
  const [online, setOnline] = useState(() => navigator.onLine);

  useEffect(() => {
    const goOnline = () => setOnline(true);
    const goOffline = () => setOnline(false);
    window.addEventListener("online", goOnline);
    window.addEventListener("offline", goOffline);
    return () => {
      window.removeEventListener("online", goOnline);
      window.removeEventListener("offline", goOffline);
    };
  }, []);

  const recheck = useCallback(() => {
    setOnline(navigator.onLine);
    return navigator.onLine;
  }, []);

  return { online, recheck };
}