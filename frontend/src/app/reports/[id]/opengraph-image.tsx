import { ImageResponse } from "next/og";
import { loadReportMeta, truncate } from "@/lib/reportSummary";

export const alt = "GhostResearcher research report";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const TEAL = "#2dd4bf";
const INK = "#0b0b0c";
const MUTE = "#a1a1aa";

/**
 * Dynamic Open Graph card rendered server-side via Satori. Shows the report
 * title plus confidence/source stats so a pasted link unfurls into a branded
 * preview in Slack, X, Discord, LinkedIn, etc. Falls back to a generic card
 * when the report can't be loaded.
 */
export default async function Image({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const meta = await loadReportMeta(id);

  const title = meta ? truncate(meta.title, 110) : "Autonomous web research";
  const stats: string[] = [];
  if (meta?.confidencePct != null) {
    stats.push(`${meta.confidencePct}% confidence`);
  }
  if (meta && meta.sourceCount > 0) {
    stats.push(`${meta.sourceCount} source${meta.sourceCount === 1 ? "" : "s"}`);
  }
  stats.push(meta?.isLongForm ? "Research paper" : "Autonomous web research");

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          background: INK,
          backgroundImage: `radial-gradient(1100px 500px at 85% -10%, rgba(45,212,191,0.16), transparent)`,
          padding: "76px 80px",
          color: "white",
          fontFamily: "sans-serif",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          <div
            style={{
              width: 44,
              height: 44,
              borderRadius: 12,
              background: TEAL,
              display: "flex",
            }}
          />
          <div
            style={{
              fontSize: 30,
              fontWeight: 700,
              letterSpacing: 6,
              color: TEAL,
            }}
          >
            GHOSTRESEARCHER
          </div>
        </div>

        <div
          style={{
            display: "flex",
            fontSize: title.length > 70 ? 60 : 72,
            fontWeight: 700,
            lineHeight: 1.08,
            letterSpacing: -1,
            maxWidth: 1040,
          }}
        >
          {title}
        </div>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 18,
            fontSize: 30,
            color: MUTE,
          }}
        >
          {stats.map((item, index) => (
            <div key={index} style={{ display: "flex", alignItems: "center", gap: 18 }}>
              {index > 0 ? <div style={{ color: "#3f3f46" }}>·</div> : null}
              <div style={{ display: "flex" }}>{item}</div>
            </div>
          ))}
        </div>
      </div>
    ),
    size,
  );
}
