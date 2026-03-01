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
import TipsAndUpdatesIcon from "@mui/icons-material/TipsAndUpdates";
import BugReportIcon from "@mui/icons-material/BugReport";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
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
            This guide walks you through using CDDBS from start to finish. Follow each step, then check the
            results listed under each section. Use the "Leave Feedback" button in the sidebar when you're done.
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

        {/* Steps */}
        <Typography variant="h5" fontWeight={800} sx={{ mb: 3 }}>
          Step-by-Step Test Walkthrough
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
            title='Create a New Analysis (click "New Analysis" button)'
            description="Fill in the analysis form. The outlet name is the news source you want to analyze. Country helps narrow SerpAPI results. URL is the outlet's website domain."
            example={`Outlet:  RT\nCountry: Russia\nURL:     rt.com\nArticles: 3\nDate:    Last Month`}
            checkItems={[
              "Form validates required fields",
              'Run appears in table with "queued" → "running" status',
              "Status auto-refreshes every few seconds",
            ]}
          />

          <StepCard
            icon={<Looks3Icon />}
            title="Wait for Analysis to Complete"
            description='The backend fetches articles via SerpAPI, sends them to Gemini for analysis, then stores results. This takes 15-60 seconds depending on article count. The status will change to "completed" or "failed".'
            checkItems={[
              "Status transitions: queued → running → completed",
              "If failed: check error message — usually an invalid API key",
              "Dashboard cards update (Total Analyses count increases)",
            ]}
          />

          <StepCard
            icon={<Looks4Icon />}
            title="View the Intelligence Briefing"
            description='Click a completed run in the table, or click the eye icon, to open the detailed briefing. The full-screen report shows the AI-generated intelligence analysis.'
            checkItems={[
              "Briefing opens in full-screen dialog",
              "Source & Context, Narrative, Analysis, Credibility sections render",
              "TL;DR summary appears at the top",
              "Article list shows on the left sidebar",
              "Quality score panel appears (if Sprint 4 is deployed)",
              "Narrative detection tags appear (if Sprint 4 is deployed)",
            ]}
          />

          <StepCard
            icon={<Looks5Icon />}
            title="Inspect Quality & Narrative Results"
            description="On the left sidebar of the briefing view, check the Quality Score panel (radar chart with 7 dimensions) and Detected Narratives panel (matched disinformation patterns)."
            checkItems={[
              "Quality score shows X/70 with a rating (Excellent/Good/etc.)",
              "Radar chart renders all 7 dimensions",
              "Hover on dimension bars to see specific issues",
              "Narrative tags show matched patterns with confidence levels",
              "Keyword chips show which terms triggered the match",
            ]}
          />
        </Stack>

        <Divider sx={{ my: 4, opacity: 0.2 }} />

        {/* Test Scenarios */}
        <Typography variant="h5" fontWeight={800} sx={{ mb: 3 }}>
          Recommended Test Scenarios
        </Typography>
        <Stack spacing={2} sx={{ mb: 4 }}>
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
              ],
            },
            {
              icon: <TipsAndUpdatesIcon sx={{ color: "#f59e0b" }} />,
              title: "AI Output Quality",
              items: [
                "Does the briefing contain hallucinated URLs or fake claims?",
                "Are confidence levels reasonable or inflated?",
                "Does the narrative detection make false positives?",
                "Is the output professional enough for an analyst?",
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
            Please use the <strong>"Leave Feedback"</strong> button in the sidebar to submit your findings.
            Your feedback directly improves this tool — be honest and specific!
          </Typography>
        </Alert>
      </Container>
    </Dialog>
  );
};
