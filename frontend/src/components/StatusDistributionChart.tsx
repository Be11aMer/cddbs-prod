import { Box, Typography, Paper, Stack } from "@mui/material";

interface Props {
    data: {
        status: string;
        count: number;
        color: string;
    }[];
}

export const StatusDistributionChart = ({ data }: Props) => {
    const total = data.reduce((acc, curr) => acc + curr.count, 0);

    // Calculate segments for visual representation
    let cumulativePercentage = 0;
    const segments = data.map((item) => {
        const percentage = total > 0 ? (item.count / total) * 100 : 0;
        const offset = cumulativePercentage;
        cumulativePercentage += percentage;
        return { ...item, percentage, offset };
    });

    return (
        <Paper
            sx={{
                p: 2,
                border: "1px solid rgba(148,163,184,0.35)",
                height: "100%",
            }}
        >
            <Typography variant="caption" color="text.secondary" sx={{ textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 600, display: "block", mb: 2 }}>
                Status Distribution
            </Typography>

            <Box sx={{ display: "flex", alignItems: "center", gap: 3 }}>
                <Box sx={{ position: "relative", width: 120, height: 120 }}>
                    <svg viewBox="0 0 36 36" style={{ width: "100%", height: "100%", transform: "rotate(-90deg)" }}>
                        {/* Background circle */}
                        <circle
                            cx="18"
                            cy="18"
                            r="15.915"
                            fill="transparent"
                            stroke="rgba(148, 163, 184, 0.1)"
                            strokeWidth="3.8"
                        />
                        {/* Segments */}
                        {segments.map((segment, index) => (
                            <circle
                                key={index}
                                cx="18"
                                cy="18"
                                r="15.915"
                                fill="transparent"
                                stroke={segment.color}
                                strokeWidth="3.8"
                                strokeDasharray={`${segment.percentage} ${100 - segment.percentage}`}
                                strokeDashoffset={-segment.offset}
                                style={{ transition: "stroke-dashoffset 0.5s ease" }}
                            />
                        ))}
                    </svg>
                    <Box
                        sx={{
                            position: "absolute",
                            top: "50%",
                            left: "50%",
                            transform: "translate(-50%, -50%)",
                            textAlign: "center",
                        }}
                    >
                        <Typography variant="h6" fontWeight={700}>
                            {total}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                            Total
                        </Typography>
                    </Box>
                </Box>

                <Stack spacing={1} sx={{ flexGrow: 1 }}>
                    {segments.map((segment, index) => (
                        <Box key={index} sx={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                                <Box sx={{ width: 8, height: 8, borderRadius: "50%", backgroundColor: segment.color }} />
                                <Typography variant="body2" color="text.secondary" sx={{ textTransform: "capitalize" }}>
                                    {segment.status}
                                </Typography>
                            </Box>
                            <Typography variant="body2" fontWeight={600}>
                                {segment.count}
                            </Typography>
                        </Box>
                    ))}
                </Stack>
            </Box>
        </Paper>
    );
};
