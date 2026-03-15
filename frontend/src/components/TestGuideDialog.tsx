import {
  Box,
  Typography,
  Paper,
  Stack,
  Divider,
  Chip,
  Alert,
  IconButton,
  Dialog,
  AppBar,
  Toolbar,
  Slide,
  Container,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import LooksOneIcon from "@mui/icons-material/LooksOne";
import LooksTwoIcon from "@mui/icons-material/LooksTwo";
import Looks3Icon from "@mui/icons-material/Looks3";
import Looks4Icon from "@mui/icons-material/Looks4";
import Looks5Icon from "@mui/icons-material/Looks5";
import Looks6Icon from "@mui/icons-material/Looks6";
import TipsAndUpdatesIcon from "@mui/icons-material/TipsAndUpdates";
import BugReportIcon from "@mui/icons-material/BugReport";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import TopicIcon from "@mui/icons-material/Hub";
import DashboardIcon from "@mui/icons-material/DashboardCustomize";
import AssessmentIcon from "@mui/icons-material/Assessment";
import { forwardRef, ReactElement, Ref } from "react";
import { TransitionProps } from "@mui/material/transitions";

const Transition = forwardRef(function Transition(
  props: TransitionProps & { children: ReactElement },
  ref: Ref<unknown>
) {
  return <Slide direction="up" ref={ref} {...props} />;
});

interface Props {
  open: boolean;
  onClose: () => void;
}

const StepCard = ({
  icon,
  title,
  description,
  example,
  checkItems,
}: {
  icon: ReactElement;
  title: string;
  description: string;
  example?: string;
  checkItems?: string[];
}) => (
  <Paper
    sx={{
      p: 3,
      borderRadius: 3,
      border: "1px solid rgba(148,163,184,0.1)",
      backgroundColor: "rgba(148,163,184,0.03)",
    }}
  >
    <Stack direction="row" spacing={2} alignItems="flex-start">
      <Box
        sx={{
          width: 44,
          height: 44,
          borderRadius: 2,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: "rgba(59,130,246,0.1)",
          color: "primary.main",
          flexShrink: 0,
        }}
      >
        {icon}
      </Box>
      <Box sx={{ flex: 1 }}>
        <Typography variant="subtitle1" fontWeight={700} gutterBottom>
          {title}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5, lineHeight: 1.7 }}>
          {description}
        </Typography>
        {example && (
          <Paper
            sx={{
              p: 2,
              borderRadius: 2,
              backgroundColor: "rgba(59,130,246,0.05)",
              border: "1px solid rgba(59,130,246,0.15)",
              mb: 1.5,
            }}
          >
            <Typography variant="caption" fontWeight={700} color="primary.light" sx={{ display: "block", mb: 0.5 }}>
              EXAMPLE
            </Typography>
            <Typography variant="body2" sx={{ fontFamily: "monospace", fontSize: "0.8rem", whiteSpace: "pre-wrap" }}>
              {example}
            </Typography>
          </Paper>
        )}
        {checkItems && (
          <Stack spacing={0.5}>
            {checkItems.map((item, i) => (
              <Stack key={i} direction="row" spacing={1} alignItems="center">
                <CheckCircleOutlineIcon sx={{ fontSize: 16, color: "success.main" }} />
                <Typography variant="caption" color="text.secondary">
                  {item}
                </Typography>
              </Stack>
            ))}
          </Stack>
        )}
      </Box>
    </Stack>
  </Paper>
);

export const TestGuideDialog = ({ open, onClose }: Props) => {
  return (
    <Dialog
      fullScreen
      open={open}
      onClose={onClose}
      TransitionComponent={Transition}
      sx={{
        "& .MuiDialog-paper": {
          backgroundColor: "#020617",
          backgroundImage:
            "radial-gradient(circle at 50% 50%, rgba(15, 23, 42, 1) 0%, rgba(2, 6, 23, 1) 100%)",
        },
      }}
    >
      <AppBar
        sx={{
          position: "relative",
          backgroundColor: "rgba(15, 23, 42, 0.8)",
          backdropFilter: "blur(12px)",
          borderBottom: "1px solid rgba(148,163,184,0.1)",
        }}
      >
        <Toolbar>
          <IconButton edge="start" color="inherit" onClick={onClose}>
            <CloseIcon />
          </IconButton>
          <Typography sx={{ ml: 2, flex: 1 }} variant="h6" fontWeight={700}>
            Test Guide & How to Use CDDBS
          </Typography>
        </Toolbar>
      </AppBar>

      <Container maxWidth="md" sx={{ py: 4 }}>
        <Alert
          severity="info"
          sx={{
            mb: 4,
            borderRadius: 3,
            backgroundColor: "rgba(59,130,246,0.05)",
            border: "1px solid rgba(59,130,246,0.2)",
          }}
        >
          <Typography variant="subtitle2" fontWeight={700}>
            Welcome, Tester!
          </Typography>
          <Typography variant="body2">
            CDDBS has grown beyond single-outlet analysis. You can now run cross-outlet topic analyses, explore a
            real-time monitoring dashboard, and browse historical reports with quality metrics. This guide walks you
            through every feature. Please test them all and use the "Leave Feedback" button in the sidebar when
            you're done — your feedback directly shapes the product.
          </Typography>
        </Alert>

        {/* Prerequisites */}
        <Typography variant="h5" fontWeight={800} sx={{ mb: 2 }}>
          Prerequisites
        </Typography>
        <Paper
          sx={{
            p: 3,
            mb: 4,
            borderRadius: 3,
            border: "1px solid rgba(245,158,11,0.2)",
            backgroundColor: "rgba(245,158,11,0.05)",
          }}
        >
          <Typography variant="body2" sx={{ lineHeight: 1.8 }}>
            You need <strong>two free API keys</strong> to use CDDBS:
          </Typography>
          <Stack spacing={1} sx={{ mt: 1.5 }}>
            <Box>
              <Chip label="1" size="small" color="primary" sx={{ mr: 1, fontWeight: 700 }} />
              <Typography variant="body2" component="span">
                <strong>SerpAPI key</strong> — sign up at{" "}
                <Typography component="span" color="primary.light" variant="body2">
                  serpapi.com
                </Typography>{" "}
                (100 free searches/month)
              </Typography>
            </Box>
            <Box>
              <Chip label="2" size="small" color="primary" sx={{ mr: 1, fontWeight: 700 }} />
              <Typography variant="body2" component="span">
                <strong>Google Gemini API key</strong> — get one at{" "}
                <Typography component="span" color="primary.light" variant="body2">
                  aistudio.google.com/apikey
                </Typography>{" "}
                (free tier available)
              </Typography>
            </Box>
          </Stack>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1.5 }}>
            Keys are stored in your browser only (localStorage). They are never sent to our server — they go directly
            to Google/SerpAPI from the backend at analysis time.
          </Typography>
        </Paper>

        {/* ========== PART 1: OUTLET ANALYSIS ========== */}
        <Typography variant="h5" fontWeight={800} sx={{ mb: 1 }}>
          Part 1 — Outlet Analysis
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          Analyze a single news outlet to generate an AI intelligence briefing with quality scoring and narrative detection.
        </Typography>
        <Stack spacing={3} sx={{ mb: 4 }}>
          <StepCard
            icon={<LooksOneIcon />}
            title="Configure Your API Keys"
            description='Click the gear icon (top-right) to open Settings. Paste your SerpAPI and Gemini keys. Click "Save Settings".'
            checkItems={[
              "Settings dialog opens without errors",
              "Keys persist after page refresh",
              'API Status section shows "Configured" for both',
            ]}
          />

          <StepCard
            icon={<LooksTwoIcon />}
            title='Create a New Outlet Analysis'
            description='Click "New Analysis", make sure the toggle is set to "Outlet Mode". Fill in the outlet name, country, domain URL, number of articles, and date filter.'
            example={`Outlet:   RT\nCountry:  Russia\nURL:      rt.com\nArticles: 3\nDate:     Last Month`}
            checkItems={[
              "Form validates required fields",
              'Run appears in table with "queued" then "running" status',
              "Status auto-refreshes every few seconds",
            ]}
          />

          <StepCard
            icon={<Looks3Icon />}
            title="View the Intelligence Briefing"
            description='Once the status changes to "completed" (15-60 seconds), click the run to open the full-screen briefing. Check the AI analysis, quality score panel (radar chart with 7 dimensions), and narrative detection tags.'
            checkItems={[
              "Briefing opens with TL;DR, Source & Context, Narrative, Analysis, Credibility sections",
              "Article list shows on the left sidebar",
              "Quality score shows X/70 with a rating (Excellent/Good/Fair/Poor)",
              "Radar chart renders all 7 dimensions — hover on bars to see specifics",
              "Narrative tags show matched disinformation patterns with confidence levels",
              "Keyword chips show which terms triggered each narrative match",
            ]}
          />
        </Stack>

        <Divider sx={{ my: 4, opacity: 0.2 }} />

        {/* ========== PART 2: TOPIC MODE ========== */}
        <Typography variant="h5" fontWeight={800} sx={{ mb: 1 }}>
          Part 2 — Topic Analysis (Cross-Outlet)
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          Discover how different outlets frame the same topic. The system fetches neutral baseline coverage from wire
          services (Reuters, AP, BBC), then compares how each discovered outlet diverges in framing and propaganda
          techniques.
        </Typography>
        <Stack spacing={3} sx={{ mb: 4 }}>
          <StepCard
            icon={<Looks4Icon />}
            title='Run a Topic Analysis'
            description='Click "New Analysis" and toggle to "Topic Mode". Enter a topic (e.g. "NATO expansion"), set the max number of outlets to discover (1-10), and choose a date filter. Submit and wait for results.'
            example={`Topic:        NATO expansion\nMax Outlets:  5\nDate:         Last Week`}
            checkItems={[
              "Toggle switches the form between Outlet Mode and Topic Mode",
              "Topic run appears in its own table or section",
              "Status progresses from queued to running to completed",
            ]}
          />

          <StepCard
            icon={<Looks5Icon />}
            title="Review Topic Results"
            description={"Open a completed topic run. You'll see a ranked list of outlets showing how each one frames the topic relative to the neutral baseline. Check the divergence score (0-100), amplification signal, and propaganda technique breakdown for each outlet."}
            checkItems={[
              "Baseline neutral coverage is displayed for comparison",
              "Each outlet shows a divergence score and amplification signal (Low/Medium/High)",
              "Propaganda techniques are identified per outlet",
              "Results make intuitive sense — state media should diverge more than wire services",
            ]}
          />
        </Stack>

        <Divider sx={{ my: 4, opacity: 0.2 }} />

        {/* ========== PART 3: MONITORING DASHBOARD ========== */}
        <Typography variant="h5" fontWeight={800} sx={{ mb: 1 }}>
          Part 3 — Monitoring Dashboard
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          The real-time intelligence dashboard shows a global overview of articles being collected, event clusters,
          narrative bursts, and country-level risk. Switch to the "Monitoring" view from the sidebar.
        </Typography>
        <Stack spacing={3} sx={{ mb: 4 }}>
          <StepCard
            icon={<Looks6Icon />}
            title="Explore the Dashboard"
            description='Click "Monitoring" in the sidebar to open the dashboard. Explore each panel: the global map, intel feed, activity timeline, narrative bar chart, event clusters, narrative trends, country risk index, and outlet network graph.'
            checkItems={[
              "Global map loads and shows country-level event dots",
              "Intel feed streams recent articles from GDELT/RSS sources",
              "Activity timeline shows a 48-hour ingestion chart",
              "Narrative bar chart displays top narratives by frequency",
              "Event cluster panel groups related articles into events with keywords",
              "Narrative trend panel shows how narratives evolve over time",
              "Country risk index ranks countries by risk score",
              "Outlet network graph visualizes connections between outlets by narrative similarity",
            ]}
          />
        </Stack>

        <Divider sx={{ my: 4, opacity: 0.2 }} />

        {/* ========== PART 4: REPORTS ========== */}
        <Typography variant="h5" fontWeight={800} sx={{ mb: 1 }}>
          Part 4 — Reports & Metrics
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          The Reports view shows all your past analyses with summary statistics. Switch to "Reports" in the sidebar.
        </Typography>
        <Stack spacing={3} sx={{ mb: 4 }}>
          <StepCard
            icon={<AssessmentIcon />}
            title="Browse Reports"
            description={"Open the \"Reports\" view. You'll see summary cards (Total Analyses, Average Quality Score, Total Narratives Detected, Success Rate) and a filterable table of all past runs. Click any completed run to revisit its full briefing."}
            checkItems={[
              "Summary cards show accurate totals matching your test runs",
              "Runs table lists all outlet and topic analyses",
              "Table is filterable and sortable",
              "Clicking a completed run opens its detailed briefing",
              "Export button lets you download analysis results as JSON",
            ]}
          />
        </Stack>

        <Divider sx={{ my: 4, opacity: 0.2 }} />

        {/* Test Scenarios */}
        <Typography variant="h5" fontWeight={800} sx={{ mb: 3 }}>
          Recommended Test Scenarios
        </Typography>

        <Typography variant="subtitle2" fontWeight={700} color="primary.light" sx={{ mb: 2 }}>
          Outlet Analysis Scenarios
        </Typography>
        <Stack spacing={2} sx={{ mb: 3 }}>
          {[
            {
              label: "State Media",
              outlet: "RT",
              country: "Russia",
              url: "rt.com",
              expect: "Should detect anti-NATO, Ukraine revisionism narratives. High propaganda scores.",
            },
            {
              label: "Mainstream Western",
              outlet: "BBC News",
              country: "United Kingdom",
              url: "bbc.com",
              expect: "Should show balanced analysis. Few or no narrative matches. Moderate-to-high quality.",
            },
            {
              label: "Chinese State",
              outlet: "CGTN",
              country: "China",
              url: "cgtn.com",
              expect: "May detect Western hypocrisy and multipolar world narratives.",
            },
            {
              label: "Edge Case: Unknown Outlet",
              outlet: "madeupnews123",
              country: "Nowhere",
              url: "madeupnews123.example",
              expect: "Should fail gracefully — SerpAPI returns no results. Check error handling.",
            },
          ].map((scenario, i) => (
            <Paper
              key={i}
              sx={{
                p: 2.5,
                borderRadius: 2,
                border: "1px solid rgba(148,163,184,0.1)",
                backgroundColor: "rgba(148,163,184,0.03)",
              }}
            >
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
                <Chip label={scenario.label} size="small" color="primary" variant="outlined" sx={{ fontWeight: 700 }} />
              </Stack>
              <Typography variant="body2" sx={{ fontFamily: "monospace", fontSize: "0.8rem", mb: 1 }}>
                Outlet: {scenario.outlet} | Country: {scenario.country} | URL: {scenario.url}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {scenario.expect}
              </Typography>
            </Paper>
          ))}
        </Stack>

        <Typography variant="subtitle2" fontWeight={700} color="primary.light" sx={{ mb: 2 }}>
          Topic Analysis Scenarios
        </Typography>
        <Stack spacing={2} sx={{ mb: 4 }}>
          {[
            {
              label: "Geopolitical",
              topic: "NATO expansion",
              outlets: 5,
              expect:
                "Should surface RT, CGTN, and others with high divergence from the neutral baseline. Western wire services should show low divergence.",
            },
            {
              label: "Economic",
              topic: "US-China trade war",
              outlets: 5,
              expect:
                "Expect divergent framing between Chinese state media and Western outlets. Look for economic nationalism narratives.",
            },
            {
              label: "Narrow Topic",
              topic: "Nord Stream pipeline sabotage",
              outlets: 3,
              expect:
                "A specific event with competing narratives. Check if the system correctly identifies blame-shifting patterns.",
            },
            {
              label: "Edge Case: Obscure Topic",
              topic: "xyznonexistenttopic123",
              outlets: 3,
              expect: "Should handle gracefully when no outlets or articles are found for the topic.",
            },
          ].map((scenario, i) => (
            <Paper
              key={i}
              sx={{
                p: 2.5,
                borderRadius: 2,
                border: "1px solid rgba(148,163,184,0.1)",
                backgroundColor: "rgba(148,163,184,0.03)",
              }}
            >
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
                <Chip label={scenario.label} size="small" color="secondary" variant="outlined" sx={{ fontWeight: 700 }} />
              </Stack>
              <Typography variant="body2" sx={{ fontFamily: "monospace", fontSize: "0.8rem", mb: 1 }}>
                Topic: {scenario.topic} | Max Outlets: {scenario.outlets}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {scenario.expect}
              </Typography>
            </Paper>
          ))}
        </Stack>

        <Divider sx={{ my: 4, opacity: 0.2 }} />

        {/* What to Look For */}
        <Typography variant="h5" fontWeight={800} sx={{ mb: 3 }}>
          What to Look For (Bug Hunting)
        </Typography>
        <Stack spacing={2} sx={{ mb: 4 }}>
          {[
            {
              icon: <BugReportIcon sx={{ color: "#ef4444" }} />,
              title: "Crashes & Errors",
              items: [
                "Does the app crash on any action?",
                "Are error messages clear and helpful?",
                "Does a failed analysis leave the UI in a broken state?",
                "Does switching between Outlet Mode and Topic Mode work cleanly?",
              ],
            },
            {
              icon: <TipsAndUpdatesIcon sx={{ color: "#f59e0b" }} />,
              title: "AI Output Quality",
              items: [
                "Does the briefing contain hallucinated URLs or fake claims?",
                "Are confidence levels reasonable or inflated?",
                "Does narrative detection produce false positives?",
                "In Topic Mode, do divergence scores make intuitive sense?",
                "Is the baseline neutral coverage accurate and well-sourced?",
                "Is the output professional enough for an analyst?",
              ],
            },
            {
              icon: <DashboardIcon sx={{ color: "#3b82f6" }} />,
              title: "Dashboard & Monitoring",
              items: [
                "Do all dashboard panels load and render data?",
                "Does the global map display correctly?",
                "Do event clusters and narrative trends update?",
                "Is the intel feed showing recent articles?",
                "Does the outlet network graph render relationships?",
              ],
            },
            {
              icon: <BugReportIcon sx={{ color: "#8b5cf6" }} />,
              title: "UX Issues",
              items: [
                "Is anything confusing or hard to find?",
                "Do buttons/links do what you expect?",
                "Does the layout break on smaller screens?",
                "Is loading state clear (do you know something is happening)?",
                "Is navigation between Monitoring, Reports, and Analysis intuitive?",
                "Do keyboard shortcuts work? (Ctrl+N for new analysis, Ctrl+R to refresh, Shift+? for help)",
              ],
            },
          ].map((section, i) => (
            <Paper
              key={i}
              sx={{
                p: 2.5,
                borderRadius: 2,
                border: "1px solid rgba(148,163,184,0.1)",
                backgroundColor: "rgba(148,163,184,0.03)",
              }}
            >
              <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mb: 1.5 }}>
                {section.icon}
                <Typography variant="subtitle2" fontWeight={700}>
                  {section.title}
                </Typography>
              </Stack>
              <Stack spacing={0.5}>
                {section.items.map((item, j) => (
                  <Typography key={j} variant="body2" color="text.secondary" sx={{ pl: 1 }}>
                    {item}
                  </Typography>
                ))}
              </Stack>
            </Paper>
          ))}
        </Stack>

        <Alert
          severity="success"
          sx={{
            borderRadius: 3,
            backgroundColor: "rgba(16,185,129,0.05)",
            border: "1px solid rgba(16,185,129,0.2)",
          }}
        >
          <Typography variant="subtitle2" fontWeight={700}>
            Done testing?
          </Typography>
          <Typography variant="body2">
            Please use the <strong>"Leave Feedback"</strong> button in the sidebar to submit your findings. Cover
            every feature you tested — Outlet Analysis, Topic Analysis, Monitoring Dashboard, and Reports. Be honest
            and specific — your feedback directly improves this tool!
          </Typography>
        </Alert>
      </Container>
    </Dialog>
  );
};
