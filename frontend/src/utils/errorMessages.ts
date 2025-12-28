/**
 * Converts technical errors into user-friendly messages
 */
export const getErrorMessage = (error: any): string => {
    // Handle Axios errors
    if (error.response) {
        const status = error.response.status;
        const data = error.response.data;

        switch (status) {
            case 400:
                return data?.message || "Invalid request. Please check your input and try again.";
            case 401:
                return "Authentication failed. Please check your API credentials in the .env file.";
            case 403:
                return "Access denied. You don't have permission to perform this action.";
            case 404:
                return "The requested resource was not found. It may have been deleted or moved.";
            case 429:
                return "Too many requests. Please wait a moment before trying again.";
            case 500:
                return "The analysis service is currently unavailable. Please try again in a few moments.";
            case 502:
            case 503:
                return "The service is temporarily unavailable. Please try again shortly.";
            case 504:
                return "The request timed out. The service may be experiencing high load.";
            default:
                return data?.message || `An unexpected error occurred (${status}). Please contact support if this persists.`;
        }
    }

    // Handle network errors
    if (error.code === "ECONNABORTED" || error.message?.includes("timeout")) {
        return "Request timed out. Please check your connection and try again.";
    }

    if (error.code === "ERR_NETWORK" || error.message?.includes("Network Error")) {
        return "Network error. Please check your internet connection.";
    }

    // Handle other errors
    if (error.message) {
        // Don't show technical stack traces to users
        if (error.message.includes("Failed to fetch")) {
            return "Unable to connect to the server. Please ensure the backend is running.";
        }
        return error.message;
    }

    return "An unexpected error occurred. Please try again.";
};

/**
 * Formats success messages for common operations
 */
export const getSuccessMessage = (operation: string): string => {
    const messages: Record<string, string> = {
        "analysis_created": "Analysis started successfully! Check the runs table for progress.",
        "analysis_deleted": "Analysis run deleted successfully.",
        "data_refreshed": "Data refreshed successfully.",
        "export_completed": "Export completed successfully.",
    };

    return messages[operation] || "Operation completed successfully.";
};
