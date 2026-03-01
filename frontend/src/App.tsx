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
  Tooltip,
} from "@mui/material";
import AssessmentIcon from "@mui/icons-material/Assessment";
import PlayCircleIcon from "@mui/icons-material/PlayCircle";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import VerifiedIcon from "@mui/icons-material/Verified";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import PushPinIcon from "@mui/icons-material/PushPin";
import PushPinOutlinedIcon from "@mui/icons-material/PushPinOutlined";
import SearchIcon from "@mui/icons-material/Search";
import InputBase from "@mui/material/InputBase";
import { styled, alpha } from "@mui/material/styles";
import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchRuns, wakeUpBackend, type RunStatus } from "./api";
import { RunsTable } from "./components/RunsTable";
import { RunDetail } from "./components/RunDetail";
import { NewAnalysisDialog } from "./components/NewAnalysisDialog";
import { StatusDistributionChart } from "./components/StatusDistributionChart";
import { ColdStartNotice } from "./components/ColdStartNotice";
import { useAppSelector } from "./hooks";
import { MetricCard } from "./components/MetricCard";
import { KeyboardShortcutsDialog } from "./components/KeyboardShortcutsDialog";
import { useKeyboardShortcuts } from "./hooks/useKeyboardShortcuts";
import { useNotification } from "./contexts/NotificationContext";
import { MetricCardSkeleton } from "./components/Skeletons";
import { SettingsDialog } from "./components/SettingsDialog";
import { ReportViewDialog } from "./components/ReportViewDialog";
import SettingsIcon from "@mui/icons-material/Settings";
import { IconButton } from "@mui/material";
import { setSelectedRunId } from "./slices/runsSlice";
import { useAppDispatch } from "./hooks";

const Search = styled("div")(({ theme }) => ({
  position: "relative",
  borderRadius: theme.shape.borderRadius * 2,
  backgroundColor: alpha(theme.palette.common.white, 0.05),
  "&:hover": {
    backgroundColor: alpha(theme.palette.common.white, 0.1),
  },
  marginRight: theme.spacing(2),
  marginLeft: 0,
  width: "100%",
  display: "flex",
  alignItems: "center",
  transition: theme.transitions.create("width"),
}));

const SearchIconWrapper = styled("div")(({ theme }) => ({
  padding: theme.spacing(0, 2),
  height: "100%",
  position: "absolute",
  pointerEvents: "none",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  color: theme.palette.text.secondary,
}));

const StyledInputBase = styled(InputBase)(({ theme }) => ({
  color: "inherit",
  width: "100%",
  "& .MuiInputBase-input": {
    padding: theme.spacing(1, 1, 1, 0),
    // vertical padding + font size from searchIcon
    paddingLeft: `calc(1em + ${theme.spacing(4)})`,
    transition: theme.transitions.create("width"),
    width: "100%",
    fontSize: "0.875rem",
  },
}));

const drawerWidth = 240;
const collapsedWidth = 8;

export const App = () => {
  const dispatch = useAppDispatch();
  const [newAnalysisOpen, setNewAnalysisOpen] = useState(false);
  const [shortcutsHelpOpen, setShortcutsHelpOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [isFirstLaunch, setIsFirstLaunch] = useState(false);
  const [reportViewOpen, setReportViewOpen] = useState(false);

  // Sidebar states
  const [isSidebarPinned, setIsSidebarPinned] = useState(() => {
    return localStorage.getItem("SIDEBAR_PINNED") === "true";
  });
  const [isSidebarHovered, setIsSidebarHovered] = useState(false);
  const [isSearchBarHovered, setIsSearchBarHovered] = useState(false);

  const selectedRunId = useAppSelector((s) => s.runs.selectedRunId);
  const { showInfo } = useNotification();

  // Persist pinned state
  useEffect(() => {
    localStorage.setItem("SIDEBAR_PINNED", isSidebarPinned.toString());
  }, [isSidebarPinned]);

  // Check for API keys on first launch
  useEffect(() => {
    const hasSerpKey = localStorage.getItem("SERPAPI_KEY");
    const hasGeminiKey = localStorage.getItem("GOOGLE_API_KEY");
    if (!hasSerpKey || !hasGeminiKey) {
      setIsFirstLaunch(true);
      setSettingsOpen(true);
    }
  }, []);

  // Wake up backend on mount
  useEffect(() => {
    wakeUpBackend();
  }, []);

  const { data: runs, refetch, isLoading } = useQuery<RunStatus[]>({
    queryKey: ["runs"],
    queryFn: fetchRuns,
    refetchInterval: (query) => {
      // Auto-refresh every 10 seconds if there are running analyses
      const data = query.state.data;
      const hasRunning = data?.some((r) => r.status === "running" || r.status === "queued");
      return hasRunning ? 10000 : false;
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

  // Quality metrics from runs data
  const runsWithQuality = runs?.filter((r) => r.quality_score != null) ?? [];
  const avgQuality = runsWithQuality.length > 0
    ? Math.round(runsWithQuality.reduce((sum, r) => sum + (r.quality_score || 0), 0) / runsWithQuality.length)
    : 0;
  const totalNarratives = runs?.reduce((sum, r) => sum + (r.narrative_count || 0), 0) ?? 0;

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
      ctrl: true,
      description: "New analysis",
      action: () => {
        setNewAnalysisOpen(true);
      },
    },
    {
      key: "r",
      ctrl: true,
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

  const toggleSidebarPinned = () => setIsSidebarPinned(!isSidebarPinned);
  const isSidebarOpen = isSidebarPinned || isSidebarHovered;

  return (
    <Box sx={{ display: "flex", minHeight: "100vh", overflowX: "hidden" }}>
      <AppBar
        position="fixed"
        sx={{
          zIndex: (theme) => theme.zIndex.drawer + 2,
          background: "transparent",
          backdropFilter: "none",
          borderBottom: "none",
          boxShadow: "none",
          width: "100%",
        }}
      >
        <Toolbar
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            borderRadius: 0,
            gap: 2,
          }}
        >
          <Box sx={{ width: 150, display: "flex", alignItems: "center" }}>
            {/* Left side spacer - allows sidebar overlap without shifting */}
          </Box>

          {/* Centered Collapsible Search Bar */}
          <Box
            onMouseEnter={() => setIsSearchBarHovered(true)}
            onMouseLeave={() => setIsSearchBarHovered(false)}
            sx={{
              flexGrow: 1,
              display: "flex",
              justifyContent: "center",
              transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
              maxWidth: isSearchBarHovered ? "40%" : "120px",
              height: 40,
              position: "relative",
            }}
          >
            {isSearchBarHovered ? (
              <Search>
                <SearchIconWrapper>
                  <SearchIcon fontSize="small" />
                </SearchIconWrapper>
                <StyledInputBase
                  placeholder="Global Search (Briefings, Entities, Tags)..."
                  inputProps={{ "aria-label": "search" }}
                  autoFocus
                />
              </Search>
            ) : (
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  gap: 1,
                  px: 2,
                  py: 1,
                  borderRadius: 5,
                  backgroundColor: "rgba(255,255,255,0.03)",
                  border: "1px solid rgba(148,163,184,0.1)",
                  cursor: "pointer",
                  "&:hover": {
                    backgroundColor: "rgba(255,255,255,0.08)",
                  }
                }}
              >
                <SearchIcon sx={{ fontSize: 18, color: "text.secondary", opacity: 0.5 }} />
                <Typography variant="caption" sx={{ color: "text.secondary", fontWeight: 600, opacity: 0.5 }}>
                  SEARCH
                </Typography>
                <Box sx={{ width: 10, height: 2, backgroundColor: "primary.main", borderRadius: 1, ml: 1, opacity: 0.3 }} />
              </Box>
            )}
          </Box>

          <Stack direction="row" spacing={1.5} alignItems="center" sx={{ width: 300, justifyContent: "flex-end" }}>
            <Button
              variant="contained"
              color="primary"
              onClick={() => setNewAnalysisOpen(true)}
              sx={{ fontWeight: 700, textTransform: "none", px: 3, borderRadius: 2 }}
            >
              New Analysis{" "}
              <Box
                component="span"
                sx={{
                  ml: 1,
                  px: 0.6,
                  py: 0.2,
                  borderRadius: 0.5,
                  backgroundColor: "rgba(255,255,255,0.2)",
                  fontSize: "0.7rem",
                }}
              >
                N
              </Box>
            </Button>
            <IconButton
              onClick={() => setSettingsOpen(true)}
              sx={{ color: "white", backgroundColor: "rgba(255,255,255,0.05)", "&:hover": { backgroundColor: "rgba(255,255,255,0.15)" } }}
            >
              <SettingsIcon />
            </IconButton>
          </Stack>
        </Toolbar>
      </AppBar>

      {/* Hover Trigger Area */}
      {!isSidebarPinned && (
        <Box
          onMouseEnter={() => setIsSidebarHovered(true)}
          sx={{
            position: "fixed",
            left: 0,
            top: 0,
            bottom: 0,
            width: 12,
            zIndex: (theme) => theme.zIndex.drawer + 2,
            cursor: "pointer",
            "&:hover": {
              "& .visual-cue": {
                opacity: 1,
                width: 4,
              }
            }
          }}
        >
          <Box
            className="visual-cue"
            sx={{
              width: 2,
              height: "100%",
              backgroundColor: "primary.main",
              opacity: 0.3,
              transition: "all 0.2s ease",
              boxShadow: "0 0 10px rgba(59, 130, 246, 0.5)",
            }}
          />
        </Box>
      )}

      <Drawer
        variant="permanent"
        onMouseEnter={() => setIsSidebarHovered(true)}
        onMouseLeave={() => setIsSidebarHovered(false)}
        sx={{
          width: isSidebarPinned ? drawerWidth : collapsedWidth,
          flexShrink: 0,
          whiteSpace: "nowrap",
          boxSizing: "border-box",
          [`& .MuiDrawer-paper`]: {
            width: isSidebarOpen ? drawerWidth : collapsedWidth,
            transition: (theme) => theme.transitions.create("width", {
              easing: theme.transitions.easing.sharp,
              duration: theme.transitions.duration.enteringScreen,
            }),
            overflowX: "hidden",
            boxSizing: "border-box",
            backgroundColor: "#020617",
            borderRight: "1px solid rgba(148,163,184,0.1)",
            backgroundImage: "linear-gradient(to bottom, rgba(15, 23, 42, 0.5), rgba(2, 6, 23, 0.5))",
            zIndex: (theme) => isSidebarOpen ? theme.zIndex.drawer + 1 : theme.zIndex.drawer,
            boxShadow: isSidebarOpen && !isSidebarPinned ? "10px 0 30px rgba(0,0,0,0.5)" : "none",
          },
        }}
      >
        <Toolbar />
        <Box sx={{ p: 2, display: "flex", alignItems: "center", justifyContent: "space-between", mt: 1 }}>
          <Box>
            <Typography variant="h6" fontWeight={900} sx={{
              background: "linear-gradient(135deg, #3b82f6 0%, #60a5fa 100%)",
              backgroundClip: "text",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              letterSpacing: "-0.03em",
              fontSize: "1.25rem"
            }}>
              CDDBS
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: -0.5, fontWeight: 600, textTransform: "uppercase", fontSize: "0.6rem", letterSpacing: "0.05em" }}>
              Analyst Portal
            </Typography>
          </Box>
          <Tooltip title={isSidebarPinned ? "Unpin Sidebar" : "Pin Sidebar"}>
            <IconButton size="small" onClick={toggleSidebarPinned} sx={{ color: isSidebarPinned ? "primary.main" : "text.secondary" }}>
              {isSidebarPinned ? <PushPinIcon fontSize="small" /> : <PushPinOutlinedIcon fontSize="small" />}
            </IconButton>
          </Tooltip>
        </Box>

        <Divider sx={{ mx: 2, opacity: 0.1 }} />

        <Box sx={{ overflow: "auto", flexGrow: 1, mt: 2 }}>
          <List sx={{ px: 1 }}>
            <ListItem disablePadding sx={{ mb: 1 }}>
              <ListItemButton
                selected
                sx={{
                  borderRadius: 2,
                  "&.Mui-selected": {
                    backgroundColor: "rgba(59, 130, 246, 0.08)",
                    borderLeft: "3px solid #3b82f6",
                    "&:hover": {
                      backgroundColor: "rgba(59, 130, 246, 0.12)",
                    },
                  },
                }}
              >
                <ListItemText
                  primaryTypographyProps={{ fontWeight: 700, fontSize: "0.875rem" }}
                  primary="Intelligence Dashboard"
                />
              </ListItemButton>
            </ListItem>
          </List>

          <Box sx={{ px: 3, py: 2, opacity: 0.5 }}>
            <Typography variant="caption" fontWeight={800} sx={{ textTransform: "uppercase", letterSpacing: "0.1em", fontSize: "0.65rem" }}>
              Navigation
            </Typography>
          </Box>
        </Box>
      </Drawer>

      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: "100%",
          transition: (theme) => theme.transitions.create("margin", {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.leavingScreen,
          }),
          marginLeft: 0,
          ...(isSidebarPinned && {
            marginLeft: 0, // Since it's 'permanent' and we use flex: 1, margin handles it
          }),
        }}
      >
        <Toolbar />
        <Container maxWidth="xl" sx={{ pt: 2 }}>
          <ColdStartNotice />
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
                  title="Avg Quality"
                  value={runsWithQuality.length > 0 ? `${avgQuality}/70` : "—"}
                  icon={<VerifiedIcon sx={{ fontSize: 28 }} />}
                  color={avgQuality >= 50 ? "success" : avgQuality >= 30 ? "warning" : "info"}
                  tooltip={`Average quality score across ${runsWithQuality.length} scored briefings (70 max)`}
                />
              )}
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              {isLoading && !runs ? (
                <MetricCardSkeleton />
              ) : (
                <MetricCard
                  title="Narratives"
                  value={totalNarratives}
                  icon={<WarningAmberIcon sx={{ fontSize: 28 }} />}
                  color={totalNarratives > 0 ? "warning" : "success"}
                  tooltip="Total disinformation narrative matches detected across all analyses"
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
                onOpenReport={(id) => {
                  dispatch(setSelectedRunId(id));
                  setReportViewOpen(true);
                }}
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
                <RunDetail
                  runId={selectedRunId}
                  onOpenReport={(id) => {
                    dispatch(setSelectedRunId(id));
                    setReportViewOpen(true);
                  }}
                />
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

      <SettingsDialog
        open={settingsOpen}
        onClose={() => {
          setSettingsOpen(false);
          setIsFirstLaunch(false);
        }}
        isFirstLaunch={isFirstLaunch}
      />

      <ReportViewDialog
        open={reportViewOpen}
        onClose={() => {
          setReportViewOpen(false);
          // Wait for transition to end before clearing selection
          setTimeout(() => dispatch(setSelectedRunId(null)), 300);
        }}
        runId={selectedRunId}
      />

      <KeyboardShortcutsDialog
        open={shortcutsHelpOpen}
        onClose={() => setShortcutsHelpOpen(false)}
      />
    </Box>
  );
};


