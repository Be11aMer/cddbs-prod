import { Box, Skeleton, Paper } from "@mui/material";

export const TableSkeleton = () => {
    return (
        <Paper
            sx={{
                p: 2,
                border: "1px solid rgba(148,163,184,0.35)",
                height: "100%",
                display: "flex",
                flexDirection: "column",
            }}
        >
            {/* Header */}
            <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 2 }}>
                <Skeleton variant="text" width={150} height={32} />
                <Skeleton variant="circular" width={32} height={32} />
            </Box>

            {/* Search and Filters */}
            <Box sx={{ mb: 2, display: "flex", gap: 1.5 }}>
                <Skeleton variant="rounded" height={40} sx={{ flexGrow: 1 }} />
                <Skeleton variant="rounded" width={120} height={40} />
                <Skeleton variant="rounded" width={120} height={40} />
            </Box>

            {/* Table Header */}
            <Box sx={{ display: "flex", gap: 2, mb: 1 }}>
                <Skeleton variant="text" width={60} />
                <Skeleton variant="text" width={100} />
                <Skeleton variant="text" width={100} />
                <Skeleton variant="text" width={150} />
                <Skeleton variant="text" width={100} />
            </Box>

            {/* Table Rows */}
            {[...Array(5)].map((_, index) => (
                <Box key={index} sx={{ display: "flex", gap: 2, mb: 1.5 }}>
                    <Skeleton variant="text" width={60} />
                    <Skeleton variant="text" width={100} />
                    <Skeleton variant="text" width={100} />
                    <Skeleton variant="text" width={150} />
                    <Skeleton variant="rounded" width={100} height={24} />
                </Box>
            ))}
        </Paper>
    );
};

export const DetailSkeleton = () => {
    return (
        <Paper
            sx={{
                p: 2,
                border: "1px solid rgba(148,163,184,0.35)",
                height: "100%",
                display: "flex",
                flexDirection: "column",
            }}
        >
            {/* Header */}
            <Skeleton variant="text" width={150} height={32} sx={{ mb: 2 }} />

            {/* Outlet Info */}
            <Box sx={{ mb: 2 }}>
                <Skeleton variant="text" width={60} height={16} />
                <Skeleton variant="text" width={200} height={24} sx={{ mt: 0.5 }} />
                <Skeleton variant="text" width={100} height={16} sx={{ mt: 1 }} />
                <Skeleton variant="text" width={250} height={20} sx={{ mt: 0.5 }} />
            </Box>

            {/* Articles */}
            <Box sx={{ mb: 2 }}>
                <Skeleton variant="text" width={80} height={16} sx={{ mb: 1 }} />
                {[...Array(3)].map((_, index) => (
                    <Box key={index} sx={{ mb: 1 }}>
                        <Skeleton variant="text" width="90%" height={20} />
                        <Skeleton variant="text" width="70%" height={16} />
                    </Box>
                ))}
            </Box>

            {/* Divider */}
            <Skeleton variant="rectangular" height={1} sx={{ my: 1.5 }} />

            {/* Briefing */}
            <Skeleton variant="text" width={120} height={16} sx={{ mb: 1 }} />
            <Box sx={{ flexGrow: 1 }}>
                {[...Array(8)].map((_, index) => (
                    <Skeleton key={index} variant="text" width={index % 3 === 0 ? "60%" : "95%"} sx={{ mb: 0.5 }} />
                ))}
            </Box>
        </Paper>
    );
};

export const MetricCardSkeleton = () => {
    return (
        <Paper
            sx={{
                p: 2,
                border: "1px solid rgba(148,163,184,0.35)",
            }}
        >
            <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <Box>
                    <Skeleton variant="text" width={100} height={16} />
                    <Skeleton variant="text" width={60} height={40} sx={{ mt: 0.5 }} />
                </Box>
                <Skeleton variant="circular" width={48} height={48} />
            </Box>
        </Paper>
    );
};
