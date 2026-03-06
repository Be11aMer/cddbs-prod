import { Box, Paper, Typography, SvgIconProps, Tooltip } from "@mui/material";
import { ReactElement } from "react";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import TrendingDownIcon from "@mui/icons-material/TrendingDown";

interface Props {
    title: string;
    value: string | number;
    icon: ReactElement<SvgIconProps>;
    color?: "primary" | "success" | "error" | "warning" | "info";
    trend?: {
        value: number;
        label: string;
    };
    tooltip?: string;
}

const colorMap = {
    primary: {
        bg: "rgba(59, 130, 246, 0.1)",
        border: "rgba(59, 130, 246, 0.3)",
        icon: "#3b82f6",
    },
    success: {
        bg: "rgba(16, 185, 129, 0.1)",
        border: "rgba(16, 185, 129, 0.3)",
        icon: "#10b981",
    },
    error: {
        bg: "rgba(239, 68, 68, 0.1)",
        border: "rgba(239, 68, 68, 0.3)",
        icon: "#ef4444",
    },
    warning: {
        bg: "rgba(245, 158, 11, 0.1)",
        border: "rgba(245, 158, 11, 0.3)",
        icon: "#f59e0b",
    },
    info: {
        bg: "rgba(59, 130, 246, 0.1)",
        border: "rgba(59, 130, 246, 0.3)",
        icon: "#3b82f6",
    },
    default: {
        bg: "rgba(148, 163, 184, 0.1)",
        border: "rgba(148, 163, 184, 0.3)",
        icon: "#94a3b8",
    },
};

export const MetricCard = ({ title, value, icon, color = "primary", trend, tooltip }: Props) => {
    const colors = colorMap[color] || colorMap.default;

    return (
        <Tooltip title={tooltip || ""} arrow placement="top">
            <Paper
                sx={{
                    p: 2,
                    border: `1px solid ${colors.border}`,
                    background: colors.bg,
                    backdropFilter: "blur(10px)",
                    transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
                    cursor: tooltip ? "help" : "default",
                    position: "relative",
                    overflow: "hidden",
                    "&:hover": {
                        transform: "translateY(-4px)",
                        boxShadow: `0 12px 32px ${colors.icon}20`,
                        border: `1px solid ${colors.icon}60`,
                    },
                    "&::before": {
                        content: '""',
                        position: "absolute",
                        top: -50,
                        right: -50,
                        width: 100,
                        height: 100,
                        background: `radial-gradient(circle, ${colors.icon}15 0%, transparent 70%)`,
                        borderRadius: "50%",
                    }
                }}
            >
                <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", position: "relative", zIndex: 1 }}>
                    <Box sx={{ minWidth: 0, flex: 1 }}>
                        <Typography variant="caption" color="text.secondary" sx={{ textTransform: "uppercase", letterSpacing: "0.1em", fontWeight: 600 }}>
                            {title}
                        </Typography>
                        <Typography variant="h4" fontWeight={800} sx={{ mt: 0.5, letterSpacing: "-0.02em", fontSize: { xs: "1.5rem", sm: "2rem", md: "2.125rem" } }}>
                            {value}
                        </Typography>
                        <Box sx={{ height: 24, mt: 0.5, display: "flex", alignItems: "center" }}>
                            {trend ? (
                                <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                                    {trend.value > 0 ? (
                                        <TrendingUpIcon sx={{ fontSize: 16, color: "#10b981" }} />
                                    ) : (
                                        <TrendingDownIcon sx={{ fontSize: 16, color: "#ef4444" }} />
                                    )}
                                    <Typography variant="caption" sx={{ color: trend.value > 0 ? "#10b981" : "#ef4444", fontWeight: 700 }}>
                                        {trend.value > 0 ? "+" : ""}{trend.value}%
                                    </Typography>
                                    <Typography variant="caption" color="text.secondary">
                                        {trend.label}
                                    </Typography>
                                </Box>
                            ) : (
                                <Box sx={{ height: 16 }} /> /* Spacer for alignment */
                            )}
                        </Box>
                    </Box>
                    <Box
                        sx={{
                            width: 52,
                            height: 52,
                            borderRadius: "16px",
                            background: `linear-gradient(135deg, ${colors.icon}40 0%, ${colors.icon}10 100%)`,
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            color: colors.icon,
                            border: `1px solid ${colors.icon}30`,
                            boxShadow: `0 4px 12px ${colors.icon}20`,
                        }}
                    >
                        {icon}
                    </Box>
                </Box>
            </Paper>
        </Tooltip>
    );
};
