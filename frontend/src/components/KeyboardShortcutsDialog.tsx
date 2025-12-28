import {
    Dialog,
    DialogTitle,
    DialogContent,
    IconButton,
    Box,
    Typography,
    Grid,
    Chip,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import KeyboardIcon from "@mui/icons-material/Keyboard";

interface Props {
    open: boolean;
    onClose: () => void;
}

interface Shortcut {
    keys: string;
    description: string;
    category: string;
}

const shortcuts: Shortcut[] = [
    { keys: "Ctrl/⌘ + K", description: "Focus search bar", category: "Navigation" },
    { keys: "N", description: "New analysis", category: "Actions" },
    { keys: "R", description: "Refresh data", category: "Actions" },
    { keys: "Esc", description: "Close dialog", category: "General" },
    { keys: "?", description: "Show keyboard shortcuts", category: "General" },
    { keys: "↑ / ↓", description: "Navigate table rows", category: "Navigation" },
    { keys: "Enter", description: "Open selected run", category: "Navigation" },
];

const categories = ["General", "Navigation", "Actions"];

export const KeyboardShortcutsDialog = ({ open, onClose }: Props) => {
    return (
        <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
            <DialogTitle sx={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                    <KeyboardIcon />
                    <Typography variant="h6" fontWeight={600}>
                        Keyboard Shortcuts
                    </Typography>
                </Box>
                <IconButton onClick={onClose} size="small">
                    <CloseIcon />
                </IconButton>
            </DialogTitle>
            <DialogContent>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                    Use these keyboard shortcuts to navigate faster and boost your productivity.
                </Typography>

                {categories.map((category) => (
                    <Box key={category} sx={{ mb: 3 }}>
                        <Typography
                            variant="caption"
                            color="text.secondary"
                            sx={{
                                textTransform: "uppercase",
                                fontWeight: 600,
                                letterSpacing: "0.05em",
                                display: "block",
                                mb: 1.5,
                            }}
                        >
                            {category}
                        </Typography>
                        <Grid container spacing={1.5}>
                            {shortcuts
                                .filter((s) => s.category === category)
                                .map((shortcut, index) => (
                                    <Grid item xs={12} key={index}>
                                        <Box
                                            sx={{
                                                display: "flex",
                                                alignItems: "center",
                                                justifyContent: "space-between",
                                                p: 1.5,
                                                borderRadius: 2,
                                                backgroundColor: "rgba(148, 163, 184, 0.05)",
                                                border: "1px solid rgba(148, 163, 184, 0.1)",
                                                transition: "all 0.2s ease-in-out",
                                                "&:hover": {
                                                    backgroundColor: "rgba(59, 130, 246, 0.05)",
                                                    border: "1px solid rgba(59, 130, 246, 0.2)",
                                                },
                                            }}
                                        >
                                            <Typography variant="body2">{shortcut.description}</Typography>
                                            <Chip
                                                label={shortcut.keys}
                                                size="small"
                                                sx={{
                                                    fontFamily: "monospace",
                                                    fontWeight: 600,
                                                    fontSize: "0.75rem",
                                                    backgroundColor: "rgba(59, 130, 246, 0.1)",
                                                    border: "1px solid rgba(59, 130, 246, 0.3)",
                                                }}
                                            />
                                        </Box>
                                    </Grid>
                                ))}
                        </Grid>
                    </Box>
                ))}

                <Box
                    sx={{
                        mt: 3,
                        p: 2,
                        borderRadius: 2,
                        backgroundColor: "rgba(59, 130, 246, 0.05)",
                        border: "1px solid rgba(59, 130, 246, 0.2)",
                    }}
                >
                    <Typography variant="caption" color="text.secondary">
                        <strong>Tip:</strong> Press <Chip label="?" size="small" sx={{ mx: 0.5, height: 20, fontSize: "0.7rem" }} />
                        anytime to view this help dialog.
                    </Typography>
                </Box>
            </DialogContent>
        </Dialog>
    );
};
