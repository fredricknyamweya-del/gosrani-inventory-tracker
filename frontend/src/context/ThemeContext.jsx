import { createContext, useContext, useEffect, useState } from "react";

const STORAGE_KEY = "gosrani-theme";
const ThemeContext = createContext(null);

function getInitialTheme() {
  const savedTheme = window.localStorage.getItem(STORAGE_KEY);
  return savedTheme === "dark" ? "dark" : "light";
}

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(getInitialTheme);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem(STORAGE_KEY, theme);
  }, [theme]);

  const value = {
    theme,
    toggleTheme: () => setTheme((currentTheme) => currentTheme === "light" ? "dark" : "light"),
  };

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const context = useContext(ThemeContext);

  if (!context) {
    throw new Error("useTheme must be used within a ThemeProvider");
  }

  return context;
}