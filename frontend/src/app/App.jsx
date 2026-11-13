import { BrowserRouter, Navigate, Route, Routes } from "react-router"
import LoginPage from "../pages/LoginPage"
import NotFoundPage from "../pages/NotFoundPage"
import AppLayout from "../components/AppLayout"
import { AdminRoute, ProtectedRoute } from "./routes"
import { AuthProvider } from "../context/AuthContext"
import { ThemeProvider } from "../context/ThemeContext"
import AssistantPage from "../pages/AssistantPage"
import InventoryPage from "../pages/InventoryPage"
import EntryFormPage from "../pages/EntryFormPage"
import CatalogPage from "../pages/CatalogPage"
import UsersPage from "../pages/UsersPage"
import EntryDetailPage from "../pages/EntryDetailPage"
import PasswordChangePage from "../pages/PasswordChangePage"
import InventorySummaryPage from "../pages/InventorySummaryPage"

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
                <Route
                  element={<InventorySummaryPage />}
                  path="inventory-summary"
                />
                <Route
                  element={<Navigate replace to="/inventory-summary" />}
                  path="catalog-summary"
                />
                <Route element={<EntryFormPage />} path="inventory/new" />
                <Route element={<EntryDetailPage />} path="inventory/:id" />
                <Route
                  element={<PasswordChangePage />}
                  path="account/password"
                />
                <Route element={<AdminRoute />}>
                  <Route
                    element={<EntryDetailPage />}
                    path="inventory/:id/edit"
                  />
                </Route>
                <Route element={<AdminRoute />}>
                  <Route element={<AssistantPage />} path="assistant" />
                  <Route element={<CatalogPage />} path="catalog" />
                  <Route element={<UsersPage />} path="users" />
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
