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

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [authError, setAuthError] = useState(null);
  const requestIdRef = useRef(0);

  const refreshUser = useCallback(async () => {
    const requestId = ++requestIdRef.current;
    setLoading(true);
    try {
      const response = await api.me();
      if (requestId !== requestIdRef.current) return;
      setUser(response.data);
      setAuthError(null);
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
    return response.data.user;
  }, []);

  const logout = useCallback(async () => {
    requestIdRef.current += 1;
    setUser(null);
    setAuthError(null);
    setLoading(false);
    try {
      await api.logout();
    } catch (error) {
      if (error.status !== 401) setAuthError(error);
    }
  }, []);

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