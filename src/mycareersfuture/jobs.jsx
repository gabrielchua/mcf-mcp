import React, { useRef, useEffect, useState, useSyncExternalStore } from "react";
import { ChevronLeft, ChevronRight, ExternalLink } from "lucide-react";

// Hook to reactively read toolOutput from window.openai
// This listens for 'openai:set_globals' events that ChatGPT dispatches
function useToolOutput() {
  const toolOutput = useSyncExternalStore(
    (onChange) => {
      const handleSetGlobals = (event) => {
        if (event.detail?.globals?.toolOutput !== undefined) {
          onChange();
        }
      };

      window.addEventListener("openai:set_globals", handleSetGlobals);
      return () => {
        window.removeEventListener("openai:set_globals", handleSetGlobals);
      };
    },
    () => {
      const output = window.openai?.toolOutput || null;
      return output;
    }
  );

  return toolOutput;
}

function formatDate(rawDate) {
  if (!rawDate) return null;
  try {
    const date = new Date(rawDate);
    return date.toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return rawDate;
  }
}

function JobCard({ job, index }) {
  const salary = job.salary || "Salary undisclosed";
  const location = job.location || job.region || "Location not listed";
  const updated = formatDate(job.updatedAt);
  const posted = formatDate(job.postedAt);

  const metaItems = [];
  if (location) metaItems.push(location);
  if (updated) metaItems.push(`Updated ${updated}`);
  if (posted && posted !== updated) metaItems.push(`Posted ${posted}`);

  const chips = [];
  if (job.employmentTypes && job.employmentTypes.length > 0) {
    chips.push(job.employmentTypes.join(" · "));
  }
  if (job.categories && job.categories.length > 0) {
    chips.push(job.categories[0]);
  }
  if (job.skills && job.skills.length > 0) {
    chips.push(`Skills: ${job.skills.slice(0, 3).join(", ")}`);
  }

  return (
    <article className="job-card">
      <div className="job-card__header">
        <span className="chip chip--number">{String(index + 1).padStart(2, "0")}</span>
        <div className="job-card__title">{job.title}</div>
        <div className="job-card__company">{job.company || "Employer undisclosed"}</div>
      </div>

      {metaItems.length > 0 && (
        <div className="job-card__meta">
          {metaItems.map((item, i) => (
            <span key={i}>{item}</span>
          ))}
        </div>
      )}

      {chips.length > 0 && (
        <div className="job-card__chips">
          {chips.map((chip, i) => (
            <span key={i} className="chip">
              {chip}
            </span>
          ))}
        </div>
      )}

      <div className="job-card__footer">
        <div className="job-card__salary">{salary}</div>
        {job.jobUrl && (
          <a
            href={job.jobUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="job-card__cta"
          >
            <span>View listing</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        )}
      </div>
    </article>
  );
}

export function App() {
  const trackRef = useRef(null);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);

  // Use reactive hook to get data from ChatGPT
  const toolOutput = useToolOutput();

  // Provide fallback data if toolOutput is null
  const data = toolOutput || {
    searchTerm: "Software Engineer",
    total: 0,
    jobs: [],
  };
  const isDefaultFallback = !toolOutput;

  const { searchTerm, total, jobs } = data;

  const updateButtons = () => {
    if (!trackRef.current) return;
    const { scrollLeft, scrollWidth, clientWidth } = trackRef.current;
    setCanScrollLeft(scrollLeft > 4);
    setCanScrollRight(scrollLeft < scrollWidth - clientWidth - 4);
  };

  useEffect(() => {
    const track = trackRef.current;
    if (!track) return;

    updateButtons();
    track.addEventListener("scroll", updateButtons, { passive: true });
    window.addEventListener("resize", updateButtons);

    return () => {
      track.removeEventListener("scroll", updateButtons);
      window.removeEventListener("resize", updateButtons);
    };
  }, [jobs]);

  const scroll = (direction) => {
    if (!trackRef.current) return;
    const scrollAmount = Math.max(trackRef.current.clientWidth * 0.8, 260);
    trackRef.current.scrollBy({
      left: direction === "left" ? -scrollAmount : scrollAmount,
      behavior: "smooth",
    });
  };

  if (!jobs || jobs.length === 0) {
    return (
      <div className="container">
        <section className="panel">
          <div className="panel-header">
            <div className="panel-title">
              {isDefaultFallback ? "Welcome to MyCareersFuture" : "No jobs found"}
            </div>
            {isDefaultFallback ? (
              <div className="panel-subtitle">
                Start by searching for a role or company to explore live listings.
              </div>
            ) : (
              <div className="panel-subtitle">
                We could not find openings on MyCareersFuture for "{searchTerm}". Try a broader
                search.
              </div>
            )}
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="container">
      <section className="panel">
        <div className="panel-header">
          <div className="panel-title">MyCareersFuture job results</div>
          <div className="panel-subtitle">
            Top matches for "{searchTerm}" · showing {jobs.length} of {total.toLocaleString()}{" "}
            results
          </div>
        </div>

        <div className="job-carousel">
          <button
            type="button"
            className={`job-carousel__button job-carousel__button--prev ${
              !canScrollLeft ? "disabled" : ""
            }`}
            onClick={() => scroll("left")}
            disabled={!canScrollLeft}
            aria-label="Scroll job cards left"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>

          <button
            type="button"
            className={`job-carousel__button job-carousel__button--next ${
              !canScrollRight ? "disabled" : ""
            }`}
            onClick={() => scroll("right")}
            disabled={!canScrollRight}
            aria-label="Scroll job cards right"
          >
            <ChevronRight className="w-5 h-5" />
          </button>

          <div ref={trackRef} className="job-carousel__track">
            {jobs.map((job, index) => (
              <JobCard key={job.id || index} job={job} index={index} />
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}

export default App;
