import { useEffect } from "react";

export interface KeyboardShortcut {
    key: string;
    ctrl?: boolean;
    meta?: boolean;
    shift?: boolean;
    alt?: boolean;
    description: string;
    action: () => void;
}

export const useKeyboardShortcuts = (shortcuts: KeyboardShortcut[]) => {
    useEffect(() => {
        const handleKeyDown = (event: KeyboardEvent) => {
            const matchingShortcut = shortcuts.find((shortcut) => {
                const keyMatches = event.key.toLowerCase() === shortcut.key.toLowerCase();
                const ctrlMatches = shortcut.ctrl ? event.ctrlKey || event.metaKey : !event.ctrlKey && !event.metaKey;
                const shiftMatches = shortcut.shift ? event.shiftKey : !event.shiftKey;
                const altMatches = shortcut.alt ? event.altKey : !event.altKey;

                return keyMatches && ctrlMatches && shiftMatches && altMatches;
            });

            if (matchingShortcut) {
                event.preventDefault();
                matchingShortcut.action();
            }
        };

        window.addEventListener("keydown", handleKeyDown);
        return () => window.removeEventListener("keydown", handleKeyDown);
    }, [shortcuts]);
};

export const getShortcutLabel = (shortcut: KeyboardShortcut): string => {
    const parts: string[] = [];

    if (shortcut.ctrl || shortcut.meta) {
        parts.push(navigator.platform.includes("Mac") ? "⌘" : "Ctrl");
    }
    if (shortcut.shift) parts.push("Shift");
    if (shortcut.alt) parts.push("Alt");
    parts.push(shortcut.key.toUpperCase());

    return parts.join(" + ");
};
