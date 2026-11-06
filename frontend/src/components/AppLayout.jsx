import {
  ClipboardList,
  KeyRound,
  LayoutDashboard,
  LogOut,
  Menu,
  PackagePlus,
  Search,
  Sparkles,
  Users,
  X,
} from "lucide-react"
import {
  Link,
  NavLink,
  Outlet,
  useLocation,
  useNavigate,
  useSearchParams,
} from "react-router"
import { useEffect, useRef, useState } from "react"
import { useApi } from "../hooks/useApi"
import { useAuth } from "../context/AuthContext"
import { api } from "../services/api"
import AssistantChat from "./AssistantChat"
import { RoleBadge } from "./ui"
import ThemeToggle from "./ThemeToggle"

function PendingRequestCount() {
  const { data, error, reload } = useApi(() => api.getCatalogRequests(), [])

  useEffect(() => {
    const refreshCount = () => {
      void reload()
    }

    window.addEventListener("catalog-requests-updated", refreshCount)
    return () => {
      window.removeEventListener("catalog-requests-updated", refreshCount)
    }
  }, [reload])

  if (error) {
    return (
      <span
        aria-label={`Unable to load pending request count: ${error.message}`}
        className="nav-count nav-count-error"
        title={error.message}
      >
        !
      </span>
    )
  }
  if (!Array.isArray(data)) return null

  const count = data.filter((request) => request.status === "Pending").length
  return (
    <span aria-label={`${count} pending requests`} className="nav-count">
      {count}
    </span>
  )
}

function initials(name = "") {
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase()
}

export default function AppLayout() {
  const { user, logout, isAdmin } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const searchQuery = searchParams.get("search") ?? "";
  const [search, setSearch] = useState(searchQuery);
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [profileOpen, setProfileOpen] = useState(false)
  const [assistantOpen, setAssistantOpen] = useState(false)
  const profileRef = useRef(null)
  const assistantTriggerRef = useRef(null)
  const assistantPanelRef = useRef(null)
  const assistantCloseRef = useRef(null)

  useEffect(() => {
    setDrawerOpen(false)
    setProfileOpen(false)
    setAssistantOpen(false)
    setSearch(searchQuery);
  }, [location.pathname, searchQuery]);

  useEffect(() => {
    if (!assistantOpen) return undefined

    const previouslyFocused = document.activeElement
    const panel = assistantPanelRef.current
    const focusableSelector =
      'a[href], button:not([disabled]), input:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'

    assistantCloseRef.current?.focus()

    function handleKeyDown(event) {
      if (event.key === "Escape") {
        setAssistantOpen(false)
        return
      }

      if (event.key !== "Tab" || !panel) return
      const focusable = [...panel.querySelectorAll(focusableSelector)]
      const firstFocusable = focusable[0]
      const lastFocusable = focusable.at(-1)

      if (!firstFocusable || !lastFocusable) {
        event.preventDefault()
        panel.focus()
      } else if (event.shiftKey && document.activeElement === firstFocusable) {
        event.preventDefault()
        lastFocusable.focus()
      } else if (!event.shiftKey && document.activeElement === lastFocusable) {
        event.preventDefault()
        firstFocusable.focus()
      }
    }

    document.addEventListener("keydown", handleKeyDown)
    return () => {
      document.removeEventListener("keydown", handleKeyDown)
      if (
        previouslyFocused instanceof HTMLElement &&
        document.contains(previouslyFocused)
      ) {
        previouslyFocused.focus()
      }
    }
  }, [assistantOpen])

  useEffect(() => {
    if (!profileOpen) return undefined

    function handlePointerDown(event) {
      if (!profileRef.current?.contains(event.target)) {
        setProfileOpen(false)
      }
    }

    function handleKeyDown(event) {
      if (event.key === "Escape") setProfileOpen(false)
    }

    document.addEventListener("pointerdown", handlePointerDown)
    document.addEventListener("keydown", handleKeyDown)
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown)
      document.removeEventListener("keydown", handleKeyDown)
    }
  }, [profileOpen])

  function handleSearch(event) {
    event.preventDefault()
    const query = search.trim()
    navigate(
      query ? `/inventory?search=${encodeURIComponent(query)}` : "/inventory",
    )
  }

  function handleLogout() {
    logout()
    navigate("/login", { replace: true })
  }

  const navigation = [
    { to: "/inventory", label: "Inventory", icon: LayoutDashboard, end: true },
    { to: "/inventory/new", label: "Add Entry", icon: PackagePlus },
    ...(isAdmin
      ? [
          { to: "/assistant", label: "AI Assistant", icon: Sparkles },
          {
            to: "/catalog",
            label: "Product Catalog",
            icon: ClipboardList,
            badge: <PendingRequestCount />,
          },
          { to: "/users", label: "User Management", icon: Users },
        ]
      : []),
  ]

  return (
    <div className={`app-shell${drawerOpen ? " drawer-open" : ""}`}>
      {drawerOpen && (
        <button
          aria-label="Close navigation"
          className="sidebar-backdrop"
          onClick={() => setDrawerOpen(false)}
          type="button"
        />
      )}

      <aside aria-label="Application sidebar" className="app-sidebar">
        <div className="sidebar-brand-row">
          <Link
            aria-label="Gosrani Wholesalers Limited, go to inventory"
            className="app-brand"
            onClick={() => setDrawerOpen(false)}
            to="/inventory"
          >
            <img
              alt="Gosrani Wholesalers Limited"
              className="app-brand-logo"
              src="/gw-logo-login.png"
            />
          </Link>
          <button
            aria-label="Close navigation"
            className="sidebar-close"
            onClick={() => setDrawerOpen(false)}
            type="button"
          >
            <X aria-hidden="true" size={19} />
          </button>
        </div>

        <div className="sidebar-section-label">WORKSPACE</div>
        <nav aria-label="Primary navigation" className="sidebar-nav">
          {navigation.map(({ to, label, icon: Icon, end, badge }) => (
            <NavLink
              aria-label={label}
              className={({ isActive }) =>
                `sidebar-link${isActive ? " is-active" : ""}`
              }
              end={end}
              key={to}
              onClick={() => setDrawerOpen(false)}
              to={to}
            >
              <Icon
                aria-hidden="true"
                className="sidebar-link-icon"
                size={18}
              />
              <span>{label}</span>
              {badge}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="sidebar-footer-brand">
            Gosrani Wholesalers Limited
          </div>
          <div>Eldoret, Kenya</div>
        </div>
      </aside>

      <div className="app-main">
        <header className="app-topbar">
          <button
            aria-expanded={drawerOpen}
            aria-label={drawerOpen ? "Close navigation" : "Open navigation"}
            className="mobile-menu-button"
            onClick={() => setDrawerOpen((open) => !open)}
            type="button"
          >
            {drawerOpen ? (
              <X aria-hidden="true" size={20} />
            ) : (
              <Menu aria-hidden="true" size={20} />
            )}
          </button>
          <div className="desktop-brand">
            <h2>GWL</h2>
            <p>Internal Business Software</p>
          </div>
          <form
            aria-label="Global inventory search"
            className="global-search"
            onSubmit={handleSearch}
          >
            <Search
              aria-hidden="true"
              className="global-search-icon"
              size={17}
            />
            <label className="sr-only" htmlFor="global-search-input">
              Search inventory
            </label>
            <input
              autoComplete="off"
              className="global-search-input"
              id="global-search-input"
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search inventory..."
              type="search"
              value={search}
            />
            <kbd>Enter</kbd>
          </form>

          <div className="topbar-actions">
            <ThemeToggle />
            <div className="profile-menu-wrap" ref={profileRef}>
              <button
                aria-expanded={profileOpen}
                aria-haspopup="menu"
                aria-label={`Open profile menu for ${user?.name ?? "your account"}`}
                className="profile-trigger"
                onClick={() => setProfileOpen((open) => !open)}
                type="button"
              >
                <span aria-hidden="true" className="profile-avatar">
                  {initials(user?.name)}
                </span>
                <span className="profile-trigger-copy">
                  <strong>{user?.name}</strong>
                  <RoleBadge role={user?.role} />
                </span>
              </button>
              {profileOpen && (
                <div className="profile-menu" role="menu">
                  <div className="profile-menu-user">
                    <strong>{user?.name}</strong>
                    <span>{user?.email}</span>
                  </div>
                  <Link
                    className="profile-menu-action"
                    onClick={() => setProfileOpen(false)}
                    role="menuitem"
                    to="/account/password"
                  >
                    <KeyRound aria-hidden="true" size={16} />
                    Change password
                  </Link>
                  <button
                    className="profile-menu-action"
                    onClick={handleLogout}
                    role="menuitem"
                    type="button"
                  >
                    <LogOut aria-hidden="true" size={16} />
                    Sign out
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        <main className="app-content">
          <Outlet />
        </main>
        <footer className="app-footer">
          <span>© {new Date().getFullYear()} Gosrani Wholesalers Limited</span>
          <span>Eldoret, Kenya</span>
        </footer>
      </div>
      {isAdmin && (
        <button
          aria-controls="assistant-panel"
          aria-expanded={assistantOpen}
          aria-label={assistantOpen ? "Close AI assistant" : "Open AI assistant"}
          className="assistant-launcher"
          onClick={() => setAssistantOpen((open) => !open)}
          ref={assistantTriggerRef}
          type="button"
        >
          <Sparkles aria-hidden="true" size={18} />
          <span>Assistant</span>
        </button>
      )}
      {isAdmin && assistantOpen && (
        <div
          className="assistant-panel-backdrop"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              setAssistantOpen(false)
            }
          }}
          role="presentation"
        >
          <section
            aria-labelledby="assistant-panel-title"
            aria-modal="true"
            className="assistant-panel"
            id="assistant-panel"
            ref={assistantPanelRef}
            role="dialog"
            tabIndex={-1}
          >
            <header className="assistant-panel-header">
              <div>
                <span>ADMIN WORKSPACE</span>
                <h2 id="assistant-panel-title">AI Assistant</h2>
              </div>
              <button
                aria-label="Close AI assistant"
                className="icon-btn"
                onClick={() => setAssistantOpen(false)}
                ref={assistantCloseRef}
                type="button"
              >
                <X aria-hidden="true" size={18} />
              </button>
            </header>
            <AssistantChat compact />
          </section>
        </div>
      )}
    </div>
  )
}
