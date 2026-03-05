import { useState, memo, useCallback } from "react";
import {
  Box,
  Typography,
  IconButton,
  Tooltip,
  Dialog,
  DialogContent,
  DialogTitle,
  Chip,
  Divider,
  Paper,
} from "@mui/material";
import OpenInFullIcon from "@mui/icons-material/OpenInFull";
import CloseFullscreenIcon from "@mui/icons-material/CloseFullscreen";
import CloseIcon from "@mui/icons-material/Close";
import PublicIcon from "@mui/icons-material/Public";
import { ComposableMap, Geographies, Geography, ZoomableGroup } from "react-simple-maps";
import type { CountryStatItem } from "../api";

const GEO_URL = "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json";

// Map country name -> ISO 3166-1 numeric (as string, matches world-atlas id field)
const COUNTRY_NAME_TO_ISO: Record<string, string> = {
  "Afghanistan": "4", "Albania": "8", "Algeria": "12", "Angola": "24",
  "Argentina": "32", "Australia": "36", "Austria": "40", "Azerbaijan": "31",
  "Bangladesh": "50", "Belarus": "112", "Belgium": "56", "Bolivia": "68",
  "Bosnia and Herzegovina": "70", "Brazil": "76", "Bulgaria": "100",
  "Cambodia": "116", "Cameroon": "120", "Canada": "124", "Chile": "152",
  "China": "156", "Colombia": "170", "Croatia": "191", "Cuba": "192",
  "Czech Republic": "203", "Czechia": "203", "Denmark": "208",
  "DR Congo": "180", "Ecuador": "218", "Egypt": "818", "Ethiopia": "231",
  "Finland": "246", "France": "250", "Germany": "276", "Ghana": "288",
  "Greece": "300", "Guatemala": "320", "Hungary": "348", "India": "356",
  "Indonesia": "360", "Iran": "364", "Iraq": "368", "Ireland": "372",
  "Israel": "376", "Italy": "380", "Japan": "392", "Jordan": "400",
  "Kazakhstan": "398", "Kenya": "404", "Kuwait": "414", "Lebanon": "422",
  "Libya": "434", "Malaysia": "458", "Mali": "466", "Mexico": "484",
  "Moldova": "498", "Morocco": "504", "Myanmar": "104", "Netherlands": "528",
  "New Zealand": "554", "Nigeria": "566", "North Korea": "408",
  "Norway": "578", "Pakistan": "586", "Palestine": "275", "Panama": "591",
  "Peru": "604", "Philippines": "608", "Poland": "616", "Portugal": "620",
  "Qatar": "634", "Romania": "642", "Russia": "643", "Saudi Arabia": "682",
  "Serbia": "688", "Slovakia": "703", "Somalia": "706", "South Africa": "710",
  "South Korea": "410", "Spain": "724", "Sri Lanka": "144", "Sudan": "729",
  "Sweden": "752", "Switzerland": "756", "Syria": "760", "Taiwan": "158",
  "Thailand": "764", "Turkey": "792", "Türkiye": "792", "Ukraine": "804",
  "United Arab Emirates": "784", "United Kingdom": "826",
  "United States": "840", "USA": "840", "US": "840", "Venezuela": "862",
  "Vietnam": "704", "Yemen": "887", "Zimbabwe": "716",
};

function getRiskColor(riskScore: number, alpha = 1): string {
  if (riskScore >= 60) return `rgba(239, 68, 68, ${alpha})`;   // red - high
  if (riskScore >= 30) return `rgba(245, 158, 11, ${alpha})`;  // amber - medium
  if (riskScore > 0)   return `rgba(59, 130, 246, ${alpha})`;  // blue - monitored
  return `rgba(30, 58, 138, ${alpha})`;                         // dark - no data
}

function getRiskLabel(score: number): string {
  if (score >= 60) return "HIGH";
  if (score >= 30) return "ELEVATED";
  if (score > 0)   return "MONITORED";
  return "NO DATA";
}

interface HoveredCountry {
  name: string;
  x: number;
  y: number;
  stat?: CountryStatItem;
}

interface MapViewProps {
  countryData: Map<string, CountryStatItem>;
  expanded?: boolean;
}

const MapView = memo(({ countryData, expanded = false }: MapViewProps) => {
  const [hovered, setHovered] = useState<HoveredCountry | null>(null);

  const handleMouseEnter = useCallback(
    (geo: { properties: { name: string } }, evt: React.MouseEvent) => {
      const name = geo.properties.name;
      const stat = countryData.get(name);
      setHovered({ name, x: evt.clientX, y: evt.clientY, stat });
    },
    [countryData]
  );

  const handleMouseMove = useCallback((evt: React.MouseEvent) => {
    if (hovered) setHovered((h) => h ? { ...h, x: evt.clientX, y: evt.clientY } : null);
  }, [hovered]);

  const handleMouseLeave = useCallback(() => setHovered(null), []);

  return (
    <Box sx={{ position: "relative", width: "100%", height: "100%" }} onMouseMove={handleMouseMove}>
      <ComposableMap
        projectionConfig={{ scale: expanded ? 160 : 130, center: [10, 10] }}
        style={{ width: "100%", height: "100%" }}
      >
        <ZoomableGroup zoom={1} minZoom={0.8} maxZoom={expanded ? 8 : 1}>
          <Geographies geography={GEO_URL}>
            {({ geographies }) =>
              geographies.map((geo) => {
                const isoId = String(geo.id);
                // Find country stat by matching ISO code
                let stat: CountryStatItem | undefined;
                for (const [name, item] of countryData.entries()) {
                  if (COUNTRY_NAME_TO_ISO[name] === isoId) {
                    stat = item;
                    break;
                  }
                }
                const risk = stat?.risk_score ?? 0;
                const isHovered = hovered?.name === geo.properties.name;

                return (
                  <Geography
                    key={geo.rsmKey}
                    geography={geo}
                    onMouseEnter={(evt) => handleMouseEnter(geo, evt as unknown as React.MouseEvent)}
                    onMouseLeave={handleMouseLeave}
                    style={{
                      default: {
                        fill: getRiskColor(risk, stat ? 0.85 : 0.15),
                        stroke: "rgba(148,163,184,0.15)",
                        strokeWidth: 0.5,
                        outline: "none",
                      },
                      hover: {
                        fill: getRiskColor(risk, 1),
                        stroke: "rgba(255,255,255,0.4)",
                        strokeWidth: 1,
                        outline: "none",
                        cursor: "pointer",
                      },
                      pressed: {
                        fill: getRiskColor(risk, 1),
                        stroke: "rgba(255,255,255,0.6)",
                        strokeWidth: 1,
                        outline: "none",
                      },
                    }}
                  />
                );
              })
            }
          </Geographies>
        </ZoomableGroup>
      </ComposableMap>

      {/* Tooltip */}
      {hovered && (
        <Box
          sx={{
            position: "fixed",
            left: hovered.x + 12,
            top: hovered.y - 10,
            zIndex: 9999,
            pointerEvents: "none",
          }}
        >
          <Paper
            elevation={8}
            sx={{
              p: 1.5,
              backgroundColor: "rgba(12, 20, 56, 0.95)",
              backdropFilter: "blur(12px)",
              border: "1px solid rgba(148,163,184,0.2)",
              borderRadius: 2,
              minWidth: 160,
            }}
          >
            <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 0.5 }}>
              {hovered.name}
            </Typography>
            {hovered.stat ? (
              <>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.5 }}>
                  <Chip
                    label={getRiskLabel(hovered.stat.risk_score)}
                    size="small"
                    sx={{
                      backgroundColor: getRiskColor(hovered.stat.risk_score, 0.2),
                      color: getRiskColor(hovered.stat.risk_score),
                      border: `1px solid ${getRiskColor(hovered.stat.risk_score, 0.4)}`,
                      fontWeight: 700,
                      fontSize: "0.6rem",
                      height: 18,
                    }}
                  />
                </Box>
                <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
                  {hovered.stat.run_count} analyses · {hovered.stat.narrative_count} narratives
                </Typography>
                {hovered.stat.avg_quality != null && (
                  <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
                    Avg quality: {hovered.stat.avg_quality}/70
                  </Typography>
                )}
              </>
            ) : (
              <Typography variant="caption" color="text.secondary">
                No analysis data
              </Typography>
            )}
          </Paper>
        </Box>
      )}

      {/* Legend */}
      <Box
        sx={{
          position: "absolute",
          bottom: expanded ? 20 : 8,
          left: expanded ? 20 : 8,
          display: "flex",
          flexDirection: "column",
          gap: 0.5,
          backgroundColor: "rgba(2, 6, 23, 0.8)",
          backdropFilter: "blur(8px)",
          border: "1px solid rgba(148,163,184,0.15)",
          borderRadius: 1.5,
          p: 1,
        }}
      >
        {[
          { color: "rgba(239, 68, 68, 0.85)", label: "High Risk" },
          { color: "rgba(245, 158, 11, 0.85)", label: "Elevated" },
          { color: "rgba(59, 130, 246, 0.85)", label: "Monitored" },
          { color: "rgba(30, 58, 138, 0.15)", label: "No Data" },
        ].map(({ color, label }) => (
          <Box key={label} sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <Box sx={{ width: 10, height: 10, borderRadius: 0.5, backgroundColor: color, flexShrink: 0 }} />
            <Typography variant="caption" sx={{ fontSize: "0.62rem", color: "text.secondary", lineHeight: 1 }}>
              {label}
            </Typography>
          </Box>
        ))}
      </Box>
    </Box>
  );
});

MapView.displayName = "MapView";

interface GlobalMapProps {
  countryStats: CountryStatItem[];
}

export const GlobalMap = ({ countryStats }: GlobalMapProps) => {
  const [expanded, setExpanded] = useState(false);

  const countryData = new Map<string, CountryStatItem>(
    countryStats.map((s) => [s.country, s])
  );

  const monitoredCount = countryStats.length;
  const highRiskCount = countryStats.filter((c) => c.risk_score >= 60).length;

  return (
    <>
      {/* Compact card */}
      <Box
        sx={{
          height: "100%",
          display: "flex",
          flexDirection: "column",
          backgroundColor: "rgba(12, 20, 56, 0.6)",
          backdropFilter: "blur(10px)",
          border: "1px solid rgba(148,163,184,0.1)",
          borderRadius: 3,
          overflow: "hidden",
        }}
      >
        {/* Header */}
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            px: 2,
            py: 1.5,
            borderBottom: "1px solid rgba(148,163,184,0.08)",
            flexShrink: 0,
          }}
        >
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <PublicIcon sx={{ fontSize: 18, color: "primary.main" }} />
            <Typography variant="subtitle2" fontWeight={700}>
              Global Disinformation Map
            </Typography>
            <Chip
              label="LIVE"
              size="small"
              sx={{
                height: 16,
                fontSize: "0.55rem",
                fontWeight: 800,
                backgroundColor: "rgba(16, 185, 129, 0.15)",
                color: "#10b981",
                border: "1px solid rgba(16,185,129,0.3)",
                animation: "pulse-opacity 2s infinite",
              }}
            />
          </Box>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <Typography variant="caption" color="text.secondary">
              {monitoredCount} countries · {highRiskCount} high risk
            </Typography>
            <Tooltip title="Expand map">
              <IconButton
                size="small"
                onClick={() => setExpanded(true)}
                sx={{
                  color: "text.secondary",
                  "&:hover": { color: "primary.main", backgroundColor: "rgba(59,130,246,0.1)" },
                }}
              >
                <OpenInFullIcon sx={{ fontSize: 16 }} />
              </IconButton>
            </Tooltip>
          </Box>
        </Box>

        {/* Map */}
        <Box sx={{ flexGrow: 1, minHeight: 0, position: "relative" }}>
          <MapView countryData={countryData} />
        </Box>
      </Box>

      {/* Expanded fullscreen dialog */}
      <Dialog
        open={expanded}
        onClose={() => setExpanded(false)}
        maxWidth={false}
        fullWidth
        PaperProps={{
          sx: {
            width: "92vw",
            height: "88vh",
            maxWidth: "none",
            backgroundColor: "rgba(2, 6, 23, 0.97)",
            backdropFilter: "blur(20px)",
            border: "1px solid rgba(148,163,184,0.15)",
            borderRadius: 3,
            display: "flex",
            flexDirection: "column",
          },
        }}
      >
        <DialogTitle
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            py: 1.5,
            px: 3,
            borderBottom: "1px solid rgba(148,163,184,0.1)",
            flexShrink: 0,
          }}
        >
          <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
            <PublicIcon sx={{ color: "primary.main" }} />
            <Box>
              <Typography variant="h6" fontWeight={800}>
                Global Disinformation Intelligence Map
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Countries coloured by disinformation activity · Hover for details · Scroll to zoom · Drag to pan
              </Typography>
            </Box>
          </Box>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            {/* Summary chips */}
            <Chip
              label={`${monitoredCount} Countries Monitored`}
              size="small"
              sx={{ backgroundColor: "rgba(59,130,246,0.15)", color: "primary.light", fontWeight: 600 }}
            />
            <Chip
              label={`${highRiskCount} High Risk`}
              size="small"
              sx={{ backgroundColor: "rgba(239,68,68,0.15)", color: "#ef4444", fontWeight: 600 }}
            />
            <Divider orientation="vertical" flexItem sx={{ mx: 1 }} />
            <Tooltip title="Collapse">
              <IconButton size="small" onClick={() => setExpanded(false)} sx={{ color: "text.secondary" }}>
                <CloseFullscreenIcon fontSize="small" />
              </IconButton>
            </Tooltip>
            <Tooltip title="Close">
              <IconButton size="small" onClick={() => setExpanded(false)} sx={{ color: "text.secondary" }}>
                <CloseIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          </Box>
        </DialogTitle>

        <DialogContent sx={{ p: 0, flexGrow: 1, display: "flex", overflow: "hidden" }}>
          {/* Expanded map */}
          <Box sx={{ flexGrow: 1, position: "relative" }}>
            <MapView countryData={countryData} expanded />
          </Box>

          {/* Side panel: country risk list */}
          <Box
            sx={{
              width: 240,
              flexShrink: 0,
              borderLeft: "1px solid rgba(148,163,184,0.1)",
              overflowY: "auto",
              p: 2,
            }}
          >
            <Typography variant="caption" fontWeight={800} sx={{ textTransform: "uppercase", letterSpacing: "0.08em", color: "text.secondary", mb: 1.5, display: "block" }}>
              Country Risk Index
            </Typography>
            {countryStats.slice(0, 20).map((c, i) => (
              <Box
                key={c.country}
                sx={{
                  mb: 1.5,
                  p: 1,
                  borderRadius: 1.5,
                  backgroundColor: "rgba(255,255,255,0.03)",
                  border: "1px solid rgba(148,163,184,0.08)",
                }}
              >
                <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 0.5 }}>
                  <Typography variant="caption" fontWeight={700} sx={{ fontSize: "0.72rem" }}>
                    {i + 1}. {c.country}
                  </Typography>
                  <Typography
                    variant="caption"
                    sx={{
                      fontSize: "0.6rem",
                      fontWeight: 800,
                      color: getRiskColor(c.risk_score),
                    }}
                  >
                    {getRiskLabel(c.risk_score)}
                  </Typography>
                </Box>
                <Box
                  sx={{
                    height: 3,
                    borderRadius: 2,
                    backgroundColor: "rgba(255,255,255,0.05)",
                    overflow: "hidden",
                  }}
                >
                  <Box
                    sx={{
                      height: "100%",
                      width: `${Math.min(100, c.risk_score)}%`,
                      backgroundColor: getRiskColor(c.risk_score),
                      borderRadius: 2,
                      transition: "width 0.5s ease",
                    }}
                  />
                </Box>
                <Typography variant="caption" color="text.secondary" sx={{ fontSize: "0.62rem", display: "block", mt: 0.5 }}>
                  {c.narrative_count} narratives · {c.run_count} analyses
                </Typography>
              </Box>
            ))}
            {countryStats.length === 0 && (
              <Typography variant="caption" color="text.secondary">
                Run analyses to populate country data
              </Typography>
            )}
          </Box>
        </DialogContent>
      </Dialog>
    </>
  );
};
