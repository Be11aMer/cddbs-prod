import { useState, useEffect } from "react";
import { Alert, Box } from "@mui/material";
import { API_URL } from "../api";

export function ColdStartNotice() {
    const [isWaking, setIsWaking] = useState(true);

    useEffect(() => {
        let mounted = true;
        const checkHealth = async () => {
            try {
                const response = await fetch(`${API_URL}/health`);
                if (response.ok && mounted) {
                    setIsWaking(false);
                } else if (mounted) {
                    setTimeout(checkHealth, 2000);
                }
            } catch {
                if (mounted) {
                    setTimeout(checkHealth, 2000);
                }
            }
        };
        checkHealth();
        return () => {
            mounted = false;
        };
    }, []);

    if (!isWaking) return null;

    return (
        <Box sx={{ mt: 2, mb: 2 }}>
            <Alert severity="info" variant="outlined" sx={{
                backgroundColor: "rgba(59,130,246,0.1)",
                borderColor: "rgba(59,130,246,0.3)",
                color: "#93c5fd"
            }}>
                Backend is waking up (free tier cold start). This takes ~30s...
            </Alert>
        </Box>
    );
}
