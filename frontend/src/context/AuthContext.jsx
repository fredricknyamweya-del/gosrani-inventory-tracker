import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import { api } from "../services/api";

const AuthContext = createContext(null);
const IDLE_TIMEOUT_MS = 15 * 60 * 1000;
const LAST_ACTIVITY_KEY = "gosrani:lastActivity";

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [authError, setAuthError] = useState(null);
  const requestIdRef = useRef(0);

  const logout = useCallback(async () => {
    requestIdRef.current += 1;
    setUser(null);
    setAuthError(null);
    setLoading(false);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(LAST_ACTIVITY_KEY, "0");
    }
    try {
      await api.logout();
    } catch (error) {
      if (error.status !== 401) setAuthError(error);
    }
  }, []);

  const refreshUser = useCallback(async () => {
    const requestId = ++requestIdRef.current;
    const storedActivity =
      typeof window === "undefined"
        ? null
        : window.localStorage.getItem(LAST_ACTIVITY_KEY);
    if (storedActivity !== null) {
      const lastActivity = Number(storedActivity);
      if (
        !Number.isFinite(lastActivity) ||
        lastActivity <= 0 ||
        Date.now() - lastActivity >= IDLE_TIMEOUT_MS
      ) {
        setUser(null);
        setAuthError(null);
        setLoading(false);
        void api.logout().catch((error) => {
          if (error.status !== 401) setAuthError(error);
        });
        return;
      }
    }
    setLoading(true);
    try {
      const response = await api.me();
      if (requestId !== requestIdRef.current) return;
      setUser(response.data);
      setAuthError(null);
      if (storedActivity === null && typeof window !== "undefined") {
        window.localStorage.setItem(LAST_ACTIVITY_KEY, String(Date.now()));
      }
    } catch (error) {
      if (requestId !== requestIdRef.current) return;
      if (error.status === 401) {
        setUser(null);
        setAuthError(null);
      } else {
        setAuthError(error);
      }
    } finally {
      if (requestId === requestIdRef.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const login = useCallback(async (credentials) => {
    requestIdRef.current += 1;
    const response = await api.login(credentials);
    setUser(response.data.user);
    setAuthError(null);
    setLoading(false);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(LAST_ACTIVITY_KEY, String(Date.now()));
    }
    return response.data.user;
  }, []);

  useEffect(() => {
    if (!user || typeof window === "undefined") return undefined;

    let timeoutId;
    let endingSession = false;
    let lastSavedActivity = Number(
      window.localStorage.getItem(LAST_ACTIVITY_KEY),
    );

    const endExpiredSession = () => {
      if (endingSession) return;
      const lastActivity = Number(
        window.localStorage.getItem(LAST_ACTIVITY_KEY),
      );
      if (
        Number.isFinite(lastActivity) &&
        lastActivity > 0 &&
        Date.now() - lastActivity < IDLE_TIMEOUT_MS
      ) {
        lastSavedActivity = lastActivity;
        scheduleTimeout();
        return;
      }
      endingSession = true;
      void logout();
    };

    const scheduleTimeout = () => {
      window.clearTimeout(timeoutId);
      const elapsed = Date.now() - lastSavedActivity;
      timeoutId = window.setTimeout(
        endExpiredSession,
        Math.max(0, IDLE_TIMEOUT_MS - elapsed),
      );
    };

    const recordActivity = () => {
      const lastActivity = Number(
        window.localStorage.getItem(LAST_ACTIVITY_KEY),
      );
      if (
        !Number.isFinite(lastActivity) ||
        lastActivity <= 0 ||
        Date.now() - lastActivity >= IDLE_TIMEOUT_MS
      ) {
        endExpiredSession();
        return;
      }

      if (Number.isFinite(lastActivity) && lastActivity > 0) {
        lastSavedActivity = lastActivity;
      }
      const now = Date.now();
      if (now - lastSavedActivity >= 1000) {
        window.localStorage.setItem(LAST_ACTIVITY_KEY, String(now));
        lastSavedActivity = now;
      }
      scheduleTimeout();
    };

    const onVisibilityChange = () => {
      if (document.visibilityState === "visible") recordActivity();
    };
    const onStorage = (event) => {
      if (event.key === LAST_ACTIVITY_KEY) recordActivity();
    };

    const activityEvents = [
      "pointerdown",
      "keydown",
      "mousemove",
      "scroll",
      "touchstart",
    ];
    activityEvents.forEach((event) =>
      window.addEventListener(event, recordActivity, { passive: true }),
    );
    window.addEventListener("focus", recordActivity);
    window.addEventListener("storage", onStorage);
    document.addEventListener("visibilitychange", onVisibilityChange);
    scheduleTimeout();

    return () => {
      window.clearTimeout(timeoutId);
      activityEvents.forEach((event) =>
        window.removeEventListener(event, recordActivity),
      );
      window.removeEventListener("focus", recordActivity);
      window.removeEventListener("storage", onStorage);
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, [logout, user]);

  const value = {
    user,
    loading,
    authError,
    isAuthenticated: Boolean(user),
    isAdmin: user?.role === "Admin",
    login,
    logout,
    refreshUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }

  return context;
}