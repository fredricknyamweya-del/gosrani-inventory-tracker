import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { api } from "../services/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [authError, setAuthError] = useState(null);

  const refreshUser = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.me();
      setUser(response.data);
      setAuthError(null);
    } catch (error) {
      if (error.status === 401) {
        api.logout();
        setUser(null);
        setAuthError(null);
      } else {
        setAuthError(error);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const login = useCallback(async (credentials) => {
    const response = await api.login(credentials);
    setUser(response.data.user);
    setAuthError(null);
    return response.data.user;
  }, []);

  const logout = useCallback(() => {
    api.logout();
    setUser(null);
    setAuthError(null);
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