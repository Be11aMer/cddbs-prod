import {
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    Button,
    TextField,
    Stack,
    Typography,
    Alert,
    Link,
    Box,
} from "@mui/material";
import { useState, useEffect } from "react";

interface Props {
    open: boolean;
    onClose: () => void;
    isFirstLaunch?: boolean;
}

export const SettingsDialog = ({ open, onClose, isFirstLaunch }: Props) => {
    const [serpapiKey, setSerpapiKey] = useState("");
    const [googleApiKey, setGoogleApiKey] = useState("");

    useEffect(() => {
        if (open) {
            setSerpapiKey(localStorage.getItem("SERPAPI_KEY") || "");
            setGoogleApiKey(localStorage.getItem("GOOGLE_API_KEY") || "");
        }
    }, [open]);

    const handleSave = () => {
        localStorage.setItem("SERPAPI_KEY", serpapiKey);
        localStorage.setItem("GOOGLE_API_KEY", googleApiKey);
        onClose();
    };

    return (
        <Dialog open={open} onClose={handleSave} maxWidth="sm" fullWidth>
            <DialogTitle sx={{ fontWeight: 700 }}>
                {isFirstLaunch ? "Welcome to CDDBS! Quick Setup" : "Settings"}
            </DialogTitle>
            <DialogContent dividers>
                <Stack spacing={3} sx={{ py: 1 }}>
                    {isFirstLaunch && (
                        <Alert severity="info">
                            To run analyses, you'll need to provide your own API keys. These are stored locally in your browser and never saved on our server.
                        </Alert>
                    )}

                    <Box>
                        <Typography variant="subtitle2" gutterBottom fontWeight={600}>
                            SerpAPI Key
                        </Typography>
                        <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
                            Used to fetch the latest news articles. <Link href="https://serpapi.com/" target="_blank">Get one here</Link>.
                        </Typography>
                        <TextField
                            fullWidth
                            type="password"
                            placeholder="Enter SerpAPI key"
                            value={serpapiKey}
                            onChange={(e) => setSerpapiKey(e.target.value)}
                            size="small"
                        />
                    </Box>

                    <Box>
                        <Typography variant="subtitle2" gutterBottom fontWeight={600}>
                            Google Gemini API Key
                        </Typography>
                        <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
                            Used for AI-powered analysis and briefing generation. <Link href="https://aistudio.google.com/app/apikey" target="_blank">Get one here</Link>.
                        </Typography>
                        <TextField
                            fullWidth
                            type="password"
                            placeholder="Enter Google API key"
                            value={googleApiKey}
                            onChange={(e) => setGoogleApiKey(e.target.value)}
                            size="small"
                        />
                    </Box>
                </Stack>
            </DialogContent>
            <DialogActions sx={{ px: 3, py: 2 }}>
                <Button onClick={handleSave} variant="contained" color="primary" fullWidth>
                    Save Configuration
                </Button>
            </DialogActions>
        </Dialog>
    );
};
