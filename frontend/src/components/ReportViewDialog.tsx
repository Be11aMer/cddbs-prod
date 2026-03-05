import {
    Box,
    Dialog,
    DialogContent,
    DialogTitle,
    IconButton,
    Typography,
    Divider,
    Stack,
    Button,
    AppBar,
    Toolbar,
    Slide,
    CircularProgress,
    Link as MuiLink,
    Chip,
    Paper,
    Grid,
    Alert,
    Tooltip,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import DownloadIcon from "@mui/icons-material/Download";
import ShareIcon from "@mui/icons-material/Share";
import ArticleIcon from "@mui/icons-material/Article";
import { forwardRef, ReactElement, Ref } from "react";
import { TransitionProps } from "@mui/material/transitions";
import { useQuery } from "@tanstack/react-query";
import { fetchRun, fetchQuality, fetchNarrativeMatches } from "../api";
import type { QualityResponse, NarrativeMatchItem } from "../api";
import ReactMarkdown from "react-markdown";
import { QualityBadge } from "./QualityBadge";
import { QualityRadarChart } from "./QualityRadarChart";
import { NarrativeTags } from "./NarrativeTags";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import { useNotification } from "../contexts/NotificationContext";
import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import InfoIcon from "@mui/icons-material/Info";
import ScienceIcon from "@mui/icons-material/Science";
import FactCheckIcon from "@mui/icons-material/FactCheck";
import AssessmentIcon from "@mui/icons-material/Assessment";
import PsychologyIcon from "@mui/icons-material/Psychology";
import LinkIcon from "@mui/icons-material/Link";

const Transition = forwardRef(function Transition(
    props: TransitionProps & {
        children: ReactElement;
    },
    ref: Ref<unknown>
) {
    return <Slide direction="up" ref={ref} {...props} />;
});

interface Props {
    open: boolean;
    onClose: () => void;
    runId: number | null;
}

export const ReportViewDialog = ({ open, onClose, runId }: Props) => {
    const { showSuccess, showError } = useNotification();

    const { data, isLoading } = useQuery({
        queryKey: ["run", runId],
        queryFn: () => fetchRun(runId as number),
        enabled: !!runId && open,
        refetchInterval: (query) => {
            const data = query.state.data;
            return data && !data.final_report ? 3000 : false;
        },
    });

    const { data: quality } = useQuery<QualityResponse>({
        queryKey: ["quality", runId],
        queryFn: () => fetchQuality(runId as number),
        enabled: !!runId && open && data?.status === "completed",
    });

    const { data: narrativeMatches } = useQuery<NarrativeMatchItem[]>({
        queryKey: ["narratives", runId],
        queryFn: () => fetchNarrativeMatches(runId as number),
        enabled: !!runId && open && data?.status === "completed",
    });

    const handleCopyToClipboard = async () => {
        if (!data?.final_report) return;
        try {
            await navigator.clipboard.writeText(data.final_report);
            showSuccess("Briefing copied to clipboard!");
        } catch (error) {
            showError("Failed to copy to clipboard");
        }
    };

    const handleDownloadMarkdown = () => {
        if (!data?.final_report) return;
        const blob = new Blob([data.final_report], { type: "text/markdown" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `briefing-${data.outlet}-${data.id}.md`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        showSuccess("Briefing downloaded successfully!");
    };

    const handleShare = () => {
        // For now, just copy the URL
        navigator.clipboard.writeText(window.location.href);
        showSuccess("Link copied to clipboard! (Note: Localhost links only work for you)");
    };

    const parseSections = (markdown: string) => {
        const sections: Record<string, string> = {
            source: "",
            narrative: "",
            analysis: "",
            credibility: "",
        };

        const patterns = [
            { key: "source", regex: /(?:^|\n)\s*(?:#\s+)?(?:\d+\.\s*)?(?:Outlet and Source URL|Source)(?::|\s*\*\*|:)?/i },
            { key: "narrative", regex: /(?:^|\n)\s*(?:#\s+)?(?:\d+\.\s*)?(?:Main Narrative\/Claims|Narrative)(?::|\s*\*\*|:)?/i },
            { key: "analysis", regex: /(?:^|\n)\s*(?:#\s+)?(?:\d+\.\s*)?(?:Analysis \(patterns, tone, framing\)|Analysis)(?::|\s*\*\*|:)?/i },
            { key: "credibility", regex: /(?:^|\n)\s*(?:#\s+)?(?:\d+\.\s*)?(?:Credibility Notes)(?::|\s*\*\*|:)?/i },
        ];

        interface MatchResult {
            key: string;
            index: number;
            length: number;
        }

        const matches: MatchResult[] = [];
        for (const p of patterns) {
            const match = p.regex.exec(markdown);
            if (match) {
                matches.push({ key: p.key, index: match.index, length: match[0].length });
            }
        }

        matches.sort((a, b) => a.index - b.index);

        if (matches.length > 0) {
            for (let i = 0; i < matches.length; i++) {
                const current = matches[i];
                const next = matches[i + 1];
                const start = current.index + current.length;
                const end = next ? next.index : markdown.length;
                sections[current.key] = markdown.substring(start, end).trim();
            }
        }

        // Fallback: if narrative is empty but we have some content elsewhere, or if everything failed
        if (!sections.source && !sections.narrative && !sections.analysis && !sections.credibility) {
            sections.narrative = markdown;
        }

        return sections;
    };

    return (
        <Dialog
            fullScreen
            open={open}
            onClose={onClose}
            TransitionComponent={Transition}
            sx={{
                "& .MuiDialog-paper": {
                    backgroundColor: "#020617",
                    backgroundImage: "radial-gradient(circle at 50% 50%, rgba(15, 23, 42, 1) 0%, rgba(2, 6, 23, 1) 100%)",
                },
            }}
        >
            <AppBar sx={{ position: "relative", backgroundColor: "rgba(15, 23, 42, 0.8)", backdropFilter: "blur(12px)", borderBottom: "1px solid rgba(148,163,184,0.1)" }}>
                <Toolbar sx={{ gap: 1 }}>
                    <IconButton edge="start" color="inherit" onClick={onClose} aria-label="close">
                        <CloseIcon />
                    </IconButton>
                    <Typography sx={{ ml: 1, flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} variant="h6" component="div" fontWeight={700}>
                        Intelligence Briefing: {data?.outlet || "Loading..."}
                    </Typography>
                    <Stack direction="row" spacing={0.5}>
                        {/* Desktop: text + icon buttons */}
                        <Button
                            color="inherit"
                            startIcon={<ContentCopyIcon />}
                            onClick={handleCopyToClipboard}
                            disabled={!data?.final_report}
                            sx={{ textTransform: "none", borderRadius: 2, display: { xs: "none", sm: "inline-flex" } }}
                        >
                            Copy
                        </Button>
                        <Button
                            color="inherit"
                            startIcon={<DownloadIcon />}
                            onClick={handleDownloadMarkdown}
                            disabled={!data?.final_report}
                            sx={{ textTransform: "none", borderRadius: 2, display: { xs: "none", sm: "inline-flex" } }}
                        >
                            Download
                        </Button>
                        <Button
                            color="inherit"
                            startIcon={<ShareIcon />}
                            onClick={handleShare}
                            sx={{ textTransform: "none", borderRadius: 2, display: { xs: "none", sm: "inline-flex" } }}
                        >
                            Share
                        </Button>
                        {/* Mobile: icon-only buttons */}
                        <Tooltip title="Copy to clipboard">
                            <span>
                                <IconButton
                                    color="inherit"
                                    onClick={handleCopyToClipboard}
                                    disabled={!data?.final_report}
                                    sx={{ display: { xs: "inline-flex", sm: "none" } }}
                                >
                                    <ContentCopyIcon fontSize="small" />
                                </IconButton>
                            </span>
                        </Tooltip>
                        <Tooltip title="Download markdown">
                            <span>
                                <IconButton
                                    color="inherit"
                                    onClick={handleDownloadMarkdown}
                                    disabled={!data?.final_report}
                                    sx={{ display: { xs: "inline-flex", sm: "none" } }}
                                >
                                    <DownloadIcon fontSize="small" />
                                </IconButton>
                            </span>
                        </Tooltip>
                        <Tooltip title="Share link">
                            <IconButton
                                color="inherit"
                                onClick={handleShare}
                                sx={{ display: { xs: "inline-flex", sm: "none" } }}
                            >
                                <ShareIcon fontSize="small" />
                            </IconButton>
                        </Tooltip>
                    </Stack>
                </Toolbar>
            </AppBar>
            <DialogContent sx={{ p: { xs: 2, sm: 3, md: 4 } }}>
                <Box sx={{ maxWidth: 1000, mx: "auto", px: { xs: 0, sm: 1 } }}>
                    {isLoading ? (
                        <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", minHeight: "50vh" }}>
                            <CircularProgress size={48} />
                            <Typography sx={{ mt: 2 }} color="text.secondary">Fetching intelligence data...</Typography>
                        </Box>
                    ) : data ? (
                        <Grid container spacing={4}>
                            <Grid item xs={12} md={4}>
                                <Stack spacing={3}>
                                    <Paper sx={{ p: 3, borderRadius: 4, border: "1px solid rgba(148,163,184,0.1)", backgroundColor: "rgba(148, 163, 184, 0.03)" }}>
                                        <Typography variant="overline" color="text.secondary" fontWeight={700}>Source Information</Typography>
                                        <Typography variant="h5" fontWeight={800} sx={{ mt: 1 }}>{data.outlet}</Typography>
                                        <Typography variant="body2" color="text.secondary" gutterBottom>{data.country || "Global Region"}</Typography>

                                        {data.meta?.url && (
                                            <Box sx={{ mt: 2 }}>
                                                <Typography variant="caption" color="text.secondary" display="block">Website</Typography>
                                                <MuiLink href={data.meta.url} target="_blank" color="primary" sx={{ wordBreak: "break-all", fontSize: "0.875rem" }}>
                                                    {data.meta.url}
                                                </MuiLink>
                                            </Box>
                                        )}
                                    </Paper>

                                    {/* Quality Score Panel */}
                                    {quality && quality.total_score !== null && (
                                        <Paper sx={{ p: 3, borderRadius: 4, border: "1px solid rgba(148,163,184,0.1)", backgroundColor: "rgba(148, 163, 184, 0.03)" }}>
                                            <QualityBadge quality={quality} />
                                            {quality.dimensions && (
                                                <Box sx={{ mt: 2 }}>
                                                    <QualityRadarChart dimensions={quality.dimensions} />
                                                </Box>
                                            )}
                                        </Paper>
                                    )}

                                    {/* Narrative Matches Panel */}
                                    {narrativeMatches && narrativeMatches.length > 0 && (
                                        <Paper sx={{ p: 3, borderRadius: 4, border: "1px solid rgba(148,163,184,0.1)", backgroundColor: "rgba(148, 163, 184, 0.03)" }}>
                                            <NarrativeTags matches={narrativeMatches} />
                                        </Paper>
                                    )}

                                    <Paper sx={{ p: 3, borderRadius: 4, border: "1px solid rgba(148,163,184,0.1)", backgroundColor: "rgba(148, 163, 184, 0.03)" }}>
                                        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
                                            <Typography variant="overline" color="text.secondary" fontWeight={700}>Data Footprint</Typography>
                                            <Chip
                                                label={quality?.rating || (data.articles.length >= 3 ? "High Confidence" : "Limited Data")}
                                                size="small"
                                                color={quality?.rating === "Excellent" || quality?.rating === "Good" ? "success" : data.articles.length >= 3 ? "success" : "warning"}
                                                sx={{ height: 20, fontSize: "0.65rem", fontWeight: 700 }}
                                            />
                                        </Stack>
                                        <Typography variant="h6" fontWeight={700} sx={{ mt: 1 }}>{data.articles.length} Articles</Typography>
                                        <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 2 }}>
                                            Analysis based on {data.articles.length} processed source{data.articles.length !== 1 ? "s" : ""}
                                        </Typography>

                                        <Stack spacing={2}>
                                            {data.articles.map((article) => (
                                                <Box key={article.id} sx={{ borderLeft: "2px solid", borderColor: "primary.main", pl: 2, py: 0.5 }}>
                                                    <Tooltip title={article.title}>
                                                        <Typography variant="body2" fontWeight={600} noWrap>{article.title}</Typography>
                                                    </Tooltip>
                                                    {article.link && (
                                                        <MuiLink href={article.link} target="_blank" variant="caption" color="text.secondary" noWrap display="block">
                                                            {new URL(article.link).hostname}
                                                        </MuiLink>
                                                    )}
                                                </Box>
                                            ))}
                                        </Stack>
                                    </Paper>
                                </Stack>
                            </Grid>

                            <Grid item xs={12} md={8}>
                                <Stack spacing={3}>
                                    <Alert
                                        icon={<ScienceIcon fontSize="inherit" />}
                                        severity="info"
                                        sx={{
                                            borderRadius: 3,
                                            backgroundColor: "rgba(59, 130, 246, 0.05)",
                                            border: "1px solid rgba(59, 130, 246, 0.2)",
                                            "& .MuiAlert-message": { width: "100%" }
                                        }}
                                    >
                                        <Typography variant="subtitle2" fontWeight={700}>Experimental Research MVP</Typography>
                                        <Typography variant="caption">This briefing is generated by experimental AI models. Always verify claims against source articles.</Typography>
                                    </Alert>

                                    {data.tldr_summary && (
                                        <Paper sx={{ p: 3, borderRadius: 4, border: "1px solid rgba(148,163,184,0.2)", backgroundColor: "rgba(148, 163, 184, 0.05)" }}>
                                            <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
                                                <PsychologyIcon sx={{ color: "primary.light", fontSize: 20 }} />
                                                <Typography variant="subtitle2" fontWeight={800} sx={{ color: "primary.light", textTransform: "uppercase", letterSpacing: "1px" }}>
                                                    Briefing TL;DR
                                                </Typography>
                                            </Stack>
                                            <Typography variant="body1" sx={{ fontStyle: "italic", lineHeight: 1.6, color: "text.primary" }}>
                                                {data.tldr_summary}
                                            </Typography>
                                        </Paper>
                                    )}

                                    <Paper sx={{ p: 4, borderRadius: 4, border: "1px solid rgba(148,163,184,0.1)", backgroundColor: "rgba(148, 163, 184, 0.02)" }}>
                                        {data.final_report ? (
                                            <Box sx={{
                                                "& .MuiAccordion-root": {
                                                    backgroundColor: "transparent",
                                                    backgroundImage: "none",
                                                    boxShadow: "none",
                                                    "&:before": { display: "none" },
                                                    mb: 2,
                                                },
                                                "& .MuiAccordionSummary-root": {
                                                    px: 0,
                                                    minHeight: 48,
                                                    "&.Mui-expanded": { minHeight: 48 },
                                                },
                                                "& .MuiAccordionDetails-root": { px: 0, pt: 0 },
                                                "& p": { marginBottom: "1.2rem", lineHeight: 1.8, fontSize: "1.05rem" },
                                                "& h1, & h2, & h3": { mt: 0, mb: 2, fontWeight: 800, color: "primary.light" },
                                                "& ul, & ol": { mb: 2, pl: 3 },
                                                "& li": { mb: 1, lineHeight: 1.7 }
                                            }}>
                                                {(() => {
                                                    const sections = parseSections(data.final_report);
                                                    const renderMarkdown = (content: string) => (
                                                        <ReactMarkdown
                                                            components={{
                                                                code({ inline, className, children, ...props }: any) {
                                                                    const match = /language-(\w+)/.exec(className || "");
                                                                    return !inline && match ? (
                                                                        <SyntaxHighlighter style={vscDarkPlus} language={match[1]} PreTag="div" {...props}>
                                                                            {String(children).replace(/\n$/, "")}
                                                                        </SyntaxHighlighter>
                                                                    ) : (
                                                                        <code className={className} style={{
                                                                            backgroundColor: "rgba(59, 130, 246, 0.1)",
                                                                            padding: "2px 6px",
                                                                            borderRadius: "4px",
                                                                            fontSize: "0.85em",
                                                                            fontFamily: "monospace",
                                                                        }} {...props}>
                                                                            {children}
                                                                        </code>
                                                                    );
                                                                },
                                                            }}
                                                        >
                                                            {content}
                                                        </ReactMarkdown>
                                                    );

                                                    return (
                                                        <>
                                                            <Accordion defaultExpanded>
                                                                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                                                                    <Stack direction="row" spacing={1.5} alignItems="center">
                                                                        <LinkIcon sx={{ color: "primary.light" }} />
                                                                        <Typography variant="h6" fontWeight={800}>Source & Context</Typography>
                                                                    </Stack>
                                                                </AccordionSummary>
                                                                <AccordionDetails>
                                                                    {renderMarkdown(sections.source || "_No source information specified separately._")}
                                                                </AccordionDetails>
                                                            </Accordion>

                                                            <Accordion defaultExpanded>
                                                                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                                                                    <Stack direction="row" spacing={1.5} alignItems="center">
                                                                        <AssessmentIcon color="primary" />
                                                                        <Typography variant="h6" fontWeight={800}>Narrative</Typography>
                                                                    </Stack>
                                                                </AccordionSummary>
                                                                <AccordionDetails>
                                                                    {renderMarkdown(sections.narrative)}
                                                                </AccordionDetails>
                                                            </Accordion>

                                                            <Accordion defaultExpanded>
                                                                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                                                                    <Stack direction="row" spacing={1.5} alignItems="center">
                                                                        <PsychologyIcon color="secondary" />
                                                                        <Typography variant="h6" fontWeight={800}>Analysis</Typography>
                                                                    </Stack>
                                                                </AccordionSummary>
                                                                <AccordionDetails>
                                                                    {renderMarkdown(sections.analysis)}
                                                                </AccordionDetails>
                                                            </Accordion>

                                                            <Accordion defaultExpanded>
                                                                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                                                                    <Stack direction="row" spacing={1.5} alignItems="center">
                                                                        <FactCheckIcon sx={{ color: "#10b981" }} />
                                                                        <Typography variant="h6" fontWeight={800}>Credibility Notes</Typography>
                                                                    </Stack>
                                                                </AccordionSummary>
                                                                <AccordionDetails>
                                                                    {renderMarkdown(sections.credibility)}
                                                                </AccordionDetails>
                                                            </Accordion>
                                                        </>
                                                    );
                                                })()}
                                            </Box>
                                        ) : data.status === "failed" ? (
                                            <Box sx={{ py: 6, px: 3 }}>
                                                <Alert
                                                    severity="error"
                                                    variant="outlined"
                                                    sx={{ borderRadius: 3, mb: 4, backgroundColor: "rgba(239, 68, 68, 0.05)" }}
                                                >
                                                    <Typography variant="h6" fontWeight={700} gutterBottom>Analysis Failed</Typography>
                                                    <Typography variant="body2">{data.message || "An unexpected error occurred during the analysis pipeline."}</Typography>
                                                </Alert>

                                                <Typography variant="subtitle1" fontWeight={700} gutterBottom sx={{ color: "primary.light" }}>
                                                    Troubleshooting Guidance
                                                </Typography>
                                                <Stack spacing={2} sx={{ mt: 2 }}>
                                                    <Box sx={{ p: 2, borderRadius: 2, backgroundColor: "rgba(148, 163, 184, 0.05)", border: "1px solid rgba(148, 163, 184, 0.1)" }}>
                                                        <Typography variant="body2" fontWeight={600} gutterBottom>1. Verify API Keys</Typography>
                                                        <Typography variant="caption" color="text.secondary">
                                                            Most failures are caused by invalid or expired API keys. Open **Settings** (gear icon) and ensure both SerpAPI and Google Gemini keys are correct.
                                                        </Typography>
                                                    </Box>
                                                    <Box sx={{ p: 2, borderRadius: 2, backgroundColor: "rgba(148, 163, 184, 0.05)", border: "1px solid rgba(148, 163, 184, 0.1)" }}>
                                                        <Typography variant="body2" fontWeight={600} gutterBottom>2. Check Source URL</Typography>
                                                        <Typography variant="caption" color="text.secondary">
                                                            Ensure the domain (e.g., rt.com) is accessible and SerpAPI can fetch results for it in the specified country.
                                                        </Typography>
                                                    </Box>
                                                    <Box sx={{ p: 2, borderRadius: 2, backgroundColor: "rgba(148, 163, 184, 0.05)", border: "1px solid rgba(148, 163, 184, 0.1)" }}>
                                                        <Typography variant="body2" fontWeight={600} gutterBottom>3. Network Issues</Typography>
                                                        <Typography variant="caption" color="text.secondary">
                                                            The backend may have encountered a temporary timeout. You can try running the analysis again in a few moments.
                                                        </Typography>
                                                    </Box>
                                                </Stack>
                                            </Box>
                                        ) : (
                                            <Box sx={{ py: 10, textAlign: "center" }}>
                                                <CircularProgress size={40} sx={{ mb: 3 }} />
                                                <Typography variant="h6" fontWeight={700}>Synthesizing Intelligence...</Typography>
                                                <Typography color="text.secondary" sx={{ mt: 1, maxWidth: 400, mx: "auto" }}>
                                                    Our models are processing the narratives and drafting your detailed briefing.
                                                </Typography>
                                            </Box>
                                        )}
                                    </Paper>
                                </Stack>
                            </Grid>
                        </Grid>
                    ) : null}
                </Box>
            </DialogContent>
        </Dialog>
    );
};
