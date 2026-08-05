"use client";

import { useEffect, useState } from "react";
import { JobCard } from "@/components/JobCard";
import { api, getUserId } from "@/lib/api";
import type { BookmarkedJob, RankedJob } from "@/types";

export default function SavedPage() {
  const [bookmarks, setBookmarks] = useState<BookmarkedJob[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      const res = await api.bookmarks(getUserId());
      setBookmarks(res.bookmarks);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const toggleSave = async (job: RankedJob) => {
    const bm = bookmarks.find((b) => b.job.id === job.id);
    if (!bm) return;
    await api.removeBookmark(getUserId(), bm.id);
    setBookmarks((prev) => prev.filter((b) => b.id !== bm.id));
  };

  return (
    <div className="mx-auto max-w-4xl px-4 py-12 sm:px-6">
      <h1 className="font-display text-4xl text-mist">Saved jobs</h1>
      <p className="mt-2 text-ink-300">
        Bookmarks stay on this device profile for quick follow-up.
      </p>
      {error && <p className="mt-4 text-sm text-red-300">{error}</p>}
      <div className="mt-8">
        {bookmarks.length === 0 ? (
          <p className="text-ink-400">No saved roles yet.</p>
        ) : (
          bookmarks.map((b) => (
            <JobCard
              key={b.id}
              job={b.job}
              saved
              onToggleSave={toggleSave}
            />
          ))
        )}
      </div>
    </div>
  );
}
