import {
  Boxes,
  ClipboardList,
  LayoutDashboard,
  LogOut,
  Menu,
  PackagePlus,
  Search,
  Sparkles,
  Users,
  X,
} from "lucide-react";
import {
  Link,
  NavLink,
  Outlet,
  useLocation,
  useNavigate,
  useSearchParams,
} from "react-router";
import { useEffect, useRef, useState } from "react";
import { useApi } from "../hooks/useApi";
import { useAuth } from "../context/AuthContext";
import { api } from "../services/api";
import { RoleBadge } from "./ui";
import ThemeToggle from "./ThemeToggle";

function PendingRequestCount() {
  const { data, error } = useApi(() => api.getCatalogRequests(), []);

  if (error) {
    return (
      <span
        aria-label={`Unable to load pending request count: ${error.message}`}
        className="nav-count nav-count-error"
        title={error.message}
      >
        !
      </span>
    );
  }
  if (!Array.isArray(data)) return null;

  const count = data.filter((request) => request.status === "Pending").length;
  return (
    <span aria-label={`${count} pending requests`} className="nav-count">
      {count}
    </span>
  );
}

function initials(name = "") {
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

export default function AppLayout() {
  const { user, logout, isAdmin } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [search, setSearch] = useState(searchParams.get("search") ?? "");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const profileRef = useRef(null);

  useEffect(() => {
    setDrawerOpen(false);
    setProfileOpen(false);
    setSearch(searchParams.get("search") ?? "");
  }, [location.pathname, searchParams]);

  useEffect(() => {
    if (!profileOpen) return undefined;

    function handlePointerDown(event) {
      if (!profileRef.current?.contains(event.target)) {
        setProfileOpen(false);
      }
    }

    function handleKeyDown(event) {
      if (event.key === "Escape") setProfileOpen(false);
    }

    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [profileOpen]);

  function handleSearch(event) {
    event.preventDefault();
    const query = search.trim();
    navigate(query ? `/inventory?search=${encodeURIComponent(query)}` : "/inventory");
  }

  function handleLogout() {
    logout();
    navigate("/login", { replace: true });
  }

  const navigation = [
    { to: "/inventory", label: "Inventory", icon: LayoutDashboard, end: true },
    { to: "/inventory/new", label: "Add Entry", icon: PackagePlus },
    { to: "/assistant", label: "AI Assistant", icon: Sparkles },
    ...(isAdmin
      ? [
          {
            to: "/catalog",
            label: "Product Catalog",
            icon: ClipboardList,
            badge: <PendingRequestCount />,
          },
          { to: "/users", label: "User Management", icon: Users },
        ]
      : []),
  ];

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
            <span className="app-brand-mark"><Boxes aria-hidden="true" size={21} /></span>
            <span className="app-brand-name">
              <strong>Gosrani</strong>
              <small>WHOLESALERS LIMITED</small>
            </span>
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
              <Icon aria-hidden="true" className="sidebar-link-icon" size={18} />
              <span>{label}</span>
              {badge}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="sidebar-footer-brand">Gosrani Wholesalers Limited</div>
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
            {drawerOpen
              ? <X aria-hidden="true" size={20} />
              : <Menu aria-hidden="true" size={20} />}
          </button>
          <form
            aria-label="Global inventory search"
            className="global-search"
            onSubmit={handleSearch}
          >
            <Search aria-hidden="true" className="global-search-icon" size={17} />
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
                <span aria-hidden="true" className="profile-avatar">{initials(user?.name)}</span>
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
    </div>
  );
}