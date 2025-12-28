import React, { createContext, useContext, useState, useCallback } from "react";
import { Snackbar, Alert, AlertColor } from "@mui/material";

interface Notification {
    message: string;
    severity: AlertColor;
    duration?: number;
}

interface NotificationContextType {
    showNotification: (message: string, severity?: AlertColor, duration?: number) => void;
    showSuccess: (message: string) => void;
    showError: (message: string) => void;
    showWarning: (message: string) => void;
    showInfo: (message: string) => void;
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

export const useNotification = () => {
    const context = useContext(NotificationContext);
    if (!context) {
        throw new Error("useNotification must be used within NotificationProvider");
    }
    return context;
};

interface Props {
    children: React.ReactNode;
}

export const NotificationProvider: React.FC<Props> = ({ children }) => {
    const [notification, setNotification] = useState<Notification | null>(null);
    const [open, setOpen] = useState(false);

    const showNotification = useCallback(
        (message: string, severity: AlertColor = "info", duration: number = 6000) => {
            setNotification({ message, severity, duration });
            setOpen(true);
        },
        []
    );

    const showSuccess = useCallback((message: string) => {
        showNotification(message, "success");
    }, [showNotification]);

    const showError = useCallback((message: string) => {
        showNotification(message, "error", 8000); // Errors stay longer
    }, [showNotification]);

    const showWarning = useCallback((message: string) => {
        showNotification(message, "warning");
    }, [showNotification]);

    const showInfo = useCallback((message: string) => {
        showNotification(message, "info");
    }, [showNotification]);

    const handleClose = (_event?: React.SyntheticEvent | Event, reason?: string) => {
        if (reason === "clickaway") {
            return;
        }
        setOpen(false);
    };

    return (
        <NotificationContext.Provider
            value={{ showNotification, showSuccess, showError, showWarning, showInfo }}
        >
            {children}
            <Snackbar
                open={open}
                autoHideDuration={notification?.duration ?? 6000}
                onClose={handleClose}
                anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
            >
                <Alert
                    onClose={handleClose}
                    severity={notification?.severity ?? "info"}
                    variant="filled"
                    sx={{
                        width: "100%",
                        boxShadow: "0 8px 24px rgba(0, 0, 0, 0.4)",
                    }}
                >
                    {notification?.message}
                </Alert>
            </Snackbar>
        </NotificationContext.Provider>
    );
};
