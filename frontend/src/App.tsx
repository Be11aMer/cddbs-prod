import {
  Box,
  Container,
  Divider,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Toolbar,
  Typography,
  AppBar,
  Button,
  Stack,
  Grid,
} from "@mui/material";
import AssessmentIcon from "@mui/icons-material/Assessment";
import PlayCircleIcon from "@mui/icons-material/PlayCircle";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchRuns, type RunStatus } from "./api";
import { RunsTable } from "./components/RunsTable";
import { RunDetail } from "./components/RunDetail";
import { NewAnalysisDialog } from "./components/NewAnalysisDialog";
import { StatusDistributionChart } from "./components/StatusDistributionChart";
import { useAppSelector } from "./hooks";
import { MetricCard } from "./components/MetricCard";
import { KeyboardShortcutsDialog } from "./components/KeyboardShortcutsDialog";
import { useKeyboardShortcuts } from "./hooks/useKeyboardShortcuts";
import { useNotification } from "./contexts/NotificationContext";
import { MetricCardSkeleton } from "./components/Skeletons";

const drawerWidth = 240;

export const App = () => {
  const [newAnalysisOpen, setNewAnalysisOpen] = useState(false);
  const [shortcutsHelpOpen, setShortcutsHelpOpen] = useState(false);
  const selectedRunId = useAppSelector((s) => s.runs.selectedRunId);
  const { showInfo } = useNotification();

  const { data: runs, refetch, isLoading } = useQuery<RunStatus[]>({
    queryKey: ["runs"],
    queryFn: fetchRuns,
    refetchInterval: (query) => {
      // Auto-refresh every 5 seconds if there are running analyses
      const data = query.state.data;
      const hasRunning = data?.some((r) => r.status === "running" || r.status === "queued");
      return hasRunning ? 5000 : false;
    },
  });

  // Refetch when component mounts to get latest status
  useEffect(() => {
    refetch();
  }, [refetch]);

  // Calculate metrics
  const totalRuns = runs?.length ?? 0;
  const runningCount = runs?.filter((r) => r.status === "running" || r.status === "queued").length ?? 0;
  const completedCount = runs?.filter((r) => r.status === "completed").length ?? 0;
  const successRate = totalRuns > 0 ? Math.round((completedCount / totalRuns) * 100) : 0;

  // Keyboard shortcuts
  useKeyboardShortcuts([
    {
      key: "k",
      ctrl: true,
      description: "Focus search",
      action: () => {
        const searchInput = document.querySelector('input[placeholder*="Search"]') as HTMLInputElement;
        if (searchInput) {
          searchInput.focus();
          showInfo("Search focused - start typing to filter");
        }
      },
    },
    {
      key: "n",
      description: "New analysis",
      action: () => {
        setNewAnalysisOpen(true);
      },
    },
    {
      key: "r",
      description: "Refresh",
      action: () => {
        refetch();
        showInfo("Data refreshed");
      },
    },
    {
      key: "?",
      shift: true,
      description: "Show keyboard shortcuts",
      action: () => {
        setShortcutsHelpOpen(true);
      },
    },
    {
      key: "Escape",
      description: "Close dialog",
      action: () => {
        setNewAnalysisOpen(false);
        setShortcutsHelpOpen(false);
      },
    },
  ]);

  return (
    <Box sx={{ display: "flex" }}>
      <AppBar
        position="fixed"
        sx={{
          zIndex: (theme) => theme.zIndex.drawer + 1,
          background: "linear-gradient(135deg, #0f172a 0%, #1e293b 100%)",
          backdropFilter: "blur(10px)",
          borderBottom: "1px solid rgba(148,163,184,0.3)",
          boxShadow: "0 4px 20px rgba(0, 0, 0, 0.5)",
        }}
      >
        <Toolbar
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            borderRadius: 0,
          }}
        >
          <Typography variant="h6" noWrap>
            Cybersecurity Disinformation Detection Briefing System
          </Typography>
          <Button
            variant="contained"
            color="primary"
            onClick={() => setNewAnalysisOpen(true)}
            sx={{ fontWeight: 700, textTransform: "none", px: 3 }}
          >
            New Analysis <Box component="span" sx={{ ml: 1, px: 0.6, py: 0.2, borderRadius: 0.5, backgroundColor: "rgba(255,255,255,0.2)", fontSize: "0.7rem" }}>N</Box>
          </Button>
        </Toolbar>
      </AppBar>

      <Drawer
        variant="permanent"
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          [`& .MuiDrawer-paper`]: {
            width: drawerWidth,
            boxSizing: "border-box",
            backgroundColor: "#020617",
            borderRight: "1px solid rgba(148,163,184,0.3)",
          },
        }}
      >
        <Toolbar />

        {/* Logo/Branding */}
        <Box sx={{ px: 2, py: 3, borderBottom: "1px solid rgba(148,163,184,0.2)" }}>
          <Typography variant="h6" fontWeight={700} sx={{
            background: "linear-gradient(135deg, #3b82f6 0%, #60a5fa 100%)",
            backgroundClip: "text",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            letterSpacing: "-0.02em",
          }}>
            CDDBS
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.5 }}>
            Intelligence Platform
          </Typography>
        </Box>

        <Box sx={{ overflow: "auto", flexGrow: 1 }}>
          <List sx={{ px: 1, py: 2 }}>
            <ListItem disablePadding sx={{ mb: 0.5 }}>
              <ListItemButton
                selected
                sx={{
                  borderRadius: 2,
                  "&.Mui-selected": {
                    background: "linear-gradient(135deg, rgba(59, 130, 246, 0.15) 0%, rgba(59, 130, 246, 0.05) 100%)",
                    borderLeft: "3px solid #3b82f6",
                    "&:hover": {
                      background: "linear-gradient(135deg, rgba(59, 130, 246, 0.2) 0%, rgba(59, 130, 246, 0.1) 100%)",
                    },
                  },
                }}
              >
                <ListItemText
                  primaryTypographyProps={{ fontWeight: 600, fontSize: "0.875rem" }}
                  primary="Dashboard"
                />
              </ListItemButton>
            </ListItem>
          </List>

          <Divider sx={{ mx: 2, my: 1 }} />

          <List sx={{ px: 1 }}>
            <ListItem>
              <ListItemText
                primaryTypographyProps={{
                  fontSize: "0.75rem",
                  fontWeight: 600,
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                  color: "text.secondary",
                }}
                primary="Briefings"
              />
            </ListItem>
          </List>
        </Box>
      </Drawer>

      <Box
        component="main"
        sx={{ flexGrow: 1, p: 3 }}
      >
        <Toolbar />
        <Container maxWidth="xl">
          {/* Dashboard Summary Cards */}
          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid item xs={12} sm={6} md={3}>
              {isLoading && !runs ? (
                <MetricCardSkeleton />
              ) : (
                <MetricCard
                  title="Total Analyses"
                  value={totalRuns}
                  icon={<AssessmentIcon sx={{ fontSize: 28 }} />}
                  color="info"
                  tooltip="Total number of intelligence reports generated by the system"
                />
              )}
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              {isLoading && !runs ? (
                <MetricCardSkeleton />
              ) : (
                <MetricCard
                  title="Running"
                  value={runningCount}
                  icon={<PlayCircleIcon sx={{ fontSize: 28 }} />}
                  color="primary"
                  trend={{ value: 12, label: "vs last week" }}
                  tooltip="Analyses currently in progress"
                />
              )}
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              {isLoading && !runs ? (
                <MetricCardSkeleton />
              ) : (
                <MetricCard
                  title="Completed"
                  value={completedCount}
                  icon={<CheckCircleIcon sx={{ fontSize: 28 }} />}
                  color="success"
                  trend={{ value: 8, label: "at peak time" }}
                  tooltip="Successfully generated intelligence briefings"
                />
              )}
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              {isLoading && !runs ? (
                <MetricCardSkeleton />
              ) : (
                <MetricCard
                  title="Success Rate"
                  value={`${successRate}%`}
                  icon={<TrendingUpIcon sx={{ fontSize: 28 }} />}
                  color={successRate >= 80 ? "success" : successRate >= 50 ? "warning" : "error"}
                  trend={{ value: 5, label: "vs average" }}
                  tooltip="Percentage of analyses that resulted in a complete intelligence report"
                />
              )}
            </Grid>
          </Grid>

          <Grid container spacing={3}>
            <Grid item xs={12} md={8}>
              <RunsTable
                runs={runs ?? []}
                onRefresh={refetch}
                isLoading={isLoading && !runs}
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <Stack spacing={3}>
                <StatusDistributionChart
                  data={[
                    { status: "completed", count: completedCount, color: "#10b981" },
                    { status: "running", count: runningCount, color: "#3b82f6" },
                    { status: "failed", count: runs?.filter(r => r.status === "failed").length || 0, color: "#ef4444" },
                    { status: "queued", count: runs?.filter(r => r.status === "queued").length || 0, color: "#94a3b8" },
                  ]}
                />
                <RunDetail runId={selectedRunId} />
              </Stack>
            </Grid>
          </Grid>
        </Container>
      </Box>

      <NewAnalysisDialog
        open={newAnalysisOpen}
        onClose={() => setNewAnalysisOpen(false)}
        onCreated={() => {
          setNewAnalysisOpen(false);
          refetch();
        }}
      />

      <KeyboardShortcutsDialog
        open={shortcutsHelpOpen}
        onClose={() => setShortcutsHelpOpen(false)}
      />
    </Box>
  );
};


