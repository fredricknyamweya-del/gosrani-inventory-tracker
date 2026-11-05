import { BrowserRouter, Navigate, Route, Routes } from "react-router"
import LoginPage from "../pages/LoginPage"
import NotFoundPage from "../pages/NotFoundPage"
import AppLayout from "../components/AppLayout"
import { AdminRoute, ProtectedRoute, SignedInPlaceholder } from "./routes"
import { AuthProvider } from "../context/AuthContext"
import { ThemeProvider } from "../context/ThemeContext"
import InventoryPage from "../pages/InventoryPage"
import EntryFormPage from "../pages/EntryFormPage"

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route element={<LoginPage />} path="/login" />
            <Route element={<ProtectedRoute />}>
              <Route element={<AppLayout />}>
                <Route element={<Navigate replace to="/inventory" />} index />
                <Route element={<InventoryPage />} path="inventory" />
                <Route element={<EntryFormPage />} path="inventory/new" />
                <Route element={<SignedInPlaceholder />} path="inventory/*" />
                <Route element={<AdminRoute />}>
                  <Route
                    element={<SignedInPlaceholder title="AI assistant" />}
                    path="assistant"
                  />
                  <Route
                    element={<SignedInPlaceholder title="Product catalog" />}
                    path="catalog"
                  />
                  <Route
                    element={<SignedInPlaceholder title="User management" />}
                    path="users"
                  />
                </Route>
                <Route element={<NotFoundPage />} path="*" />
              </Route>
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  )
}
