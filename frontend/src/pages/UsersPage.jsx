import {
  Check,
  Copy,
  Plus,
  RotateCcw,
  Trash2,
  UserRoundX,
} from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import {
  Button,
  EmptyState,
  ErrorState,
  Field,
  Input,
  LoadingState,
  Modal,
  PageHeader,
  RoleBadge,
  Select,
  Toast,
} from "../components/ui";
import { useAuth } from "../context/AuthContext";
import { useApi } from "../hooks/useApi";
import { api } from "../services/api";
import { formatDate } from "../utils/format";

function UserStatus({ status }) {
  return (
    <span className={`users-status is-${status.toLocaleLowerCase()}`}>
      {status}
    </span>
  );
}

export default function UsersPage() {
  const { user: signedInUser } = useAuth();
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("All");
  const [statusFilter, setStatusFilter] = useState("All");
  const [addOpen, setAddOpen] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("User");
  const [locationId, setLocationId] = useState("");
  const [addError, setAddError] = useState("");
  const [saving, setSaving] = useState(false);
  const [credential, setCredential] = useState(null);
  const [copyError, setCopyError] = useState("");
  const [copied, setCopied] = useState(false);
  const [changeTarget, setChangeTarget] = useState(null);
  const [changeError, setChangeError] = useState("");
  const [changing, setChanging] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleteError, setDeleteError] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [toast, setToast] = useState(null);
  const { data: users, error, loading, reload } = useApi(
    () => api.getUsers(),
    [],
  );
  const {
    data: locations,
    error: locationsError,
    loading: locationsLoading,
    reload: reloadLocations,
  } = useApi(() => api.getLocations(), []);

  const visibleUsers = useMemo(() => {
    const query = search.trim().toLocaleLowerCase();
    return (users ?? []).filter((entry) => {
      const matchesSearch =
        !query ||
        entry.name.toLocaleLowerCase().includes(query) ||
        entry.email.toLocaleLowerCase().includes(query);
      const matchesRole = roleFilter === "All" || entry.role === roleFilter;
      const matchesStatus =
        statusFilter === "All" || entry.status === statusFilter;
      return matchesSearch && matchesRole && matchesStatus;
    });
  }, [users, search, roleFilter, statusFilter]);
  const activeAdminCount = (users ?? []).filter(
    (entry) => entry.role === "Admin" && entry.status === "Active",
  ).length;

  async function createUser(event) {
    event.preventDefault();
    setSaving(true);
    setAddError("");
    try {
      const response = await api.createUser({
        name,
        email,
        role,
        locationIds: [Number(locationId)],
      });
      setAddOpen(false);
      setName("");
      setEmail("");
      setRole("User");
      setLocationId("");
      setCredential(response.data);
      setCopyError("");
      setCopied(false);
      await reload();
    } catch (requestError) {
      setAddError(requestError.message);
    } finally {
      setSaving(false);
    }
  }

  async function copyCredential() {
    if (!credential?.temporaryPassword) return;
    try {
      await navigator.clipboard.writeText(credential.temporaryPassword);
      setCopied(true);
      setCopyError("");
    } catch {
      setCopied(false);
      setCopyError("Unable to copy the password. Select and copy it manually.");
    }
  }

  function closeCredential() {
    setCredential(null);
    setCopyError("");
    setCopied(false);
  }

  const closeAdd = useCallback(() => {
    setAddOpen(false);
    setAddError("");
    setName("");
    setEmail("");
    setRole("User");
    setLocationId("");
  }, []);

  function requestChange(entry, changes) {
    setChangeTarget({ user: entry, changes });
    setChangeError("");
  }

  function closeChange() {
    setChangeTarget(null);
    setChangeError("");
  }

  async function confirmChange() {
    if (!changeTarget) return;
    setChanging(true);
    setChangeError("");
    try {
      await api.updateUser(changeTarget.user.id, changeTarget.changes);
      await reload();
      closeChange();
      setToast({ message: "User updated." });
    } catch (requestError) {
      setChangeError(requestError.message);
    } finally {
      setChanging(false);
    }
  }

  function requestDelete(entry) {
    setDeleteTarget(entry);
    setDeleteError("");
  }

  function closeDelete() {
    if (deleting) return;
    setDeleteTarget(null);
    setDeleteError("");
  }

  async function confirmDelete() {
    if (!deleteTarget) return;
    setDeleting(true);
    setDeleteError("");
    try {
      await api.deleteUser(deleteTarget.id);
      setDeleteTarget(null);
      setToast({ message: "User deleted." });
      await reload();
    } catch (requestError) {
      setDeleteError(requestError.message);
    } finally {
      setDeleting(false);
    }
  }

  if (loading) {
    return (
      <>
        <PageHeader title="User management" />
        <section className="panel">
          <LoadingState label="Loading users" rows={5} />
        </section>
      </>
    );
  }

  if (error) {
    return (
      <ErrorState
        message={error.message}
        onRetry={reload}
        retrying={loading}
        title={error.status === 403 ? "Access forbidden" : "Unable to load users"}
      />
    );
  }

  return (
    <section className="users-page">
      <PageHeader
        actions={
          <Button onClick={() => setAddOpen(true)}>
            <Plus aria-hidden="true" size={17} />
            Add user
          </Button>
        }
        className="users-page-header"
        details={
          <section aria-label="User filters" className="panel users-toolbar">
            <label className="users-search">
              <span className="sr-only">Search users by name or email</span>
              <Input
                autoComplete="off"
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search name or email..."
                type="search"
                value={search}
              />
            </label>
            <label className="users-filter">
              <span>Role</span>
              <Select
                aria-label="Filter users by role"
                onChange={(event) => setRoleFilter(event.target.value)}
                value={roleFilter}
              >
                <option>All</option>
                <option>Admin</option>
                <option>User</option>
              </Select>
            </label>
            <label className="users-filter">
              <span>Status</span>
              <Select
                aria-label="Filter users by status"
                onChange={(event) => setStatusFilter(event.target.value)}
                value={statusFilter}
              >
                <option>All</option>
                <option>Active</option>
                <option>Inactive</option>
              </Select>
            </label>
          </section>
        }
        description="Manage staff access to the inventory system."
        eyebrow="Administration"
        title="User management"
      />

      {visibleUsers.length === 0 ? (
        <section className="panel">
          <EmptyState
            action={
              users?.length ? undefined : (
                <Button onClick={() => setAddOpen(true)}>
                  <Plus aria-hidden="true" size={17} />
                  Add user
                </Button>
              )
            }
            description={
              users?.length
                ? "Try changing the search or filters."
                : "Add a user to grant them access."
            }
            title={users?.length ? "No matching users" : "No users found"}
          />
        </section>
      ) : (
        <div className="panel table-scroll">
          <table className="data-table users-table">
            <thead>
              <tr>
                <th scope="col">Name</th>
                <th scope="col">Email</th>
                <th scope="col">Role</th>
                <th scope="col">Status</th>
                <th scope="col">Created</th>
                <th scope="col">Actions</th>
              </tr>
            </thead>
            <tbody>
              {visibleUsers.map((entry) => {
                const isSelf = entry.id === signedInUser?.id;
                const isLastActiveAdmin =
                  entry.role === "Admin" &&
                  entry.status === "Active" &&
                  activeAdminCount <= 1;
                return (
                  <tr key={entry.id}>
                    <td>
                      <div className="users-name-cell">
                        <strong>{entry.name}</strong>
                        {isSelf && <span className="users-you-badge">You</span>}
                      </div>
                    </td>
                    <td>{entry.email}</td>
                    <td>
                      <div className="users-role-cell">
                        <RoleBadge role={entry.role} />
                        <Select
                          aria-label={`Change role for ${entry.name}`}
                          onChange={(event) => {
                            if (event.target.value === entry.role) return;
                            requestChange(entry, { role: event.target.value });
                          }}
                          value={entry.role}
                        >
                          <option>Admin</option>
                          <option>User</option>
                        </Select>
                      </div>
                    </td>
                    <td>
                      <UserStatus status={entry.status} />
                    </td>
                    <td>{formatDate(entry.createdAt)}</td>
                    <td>
                      <div className="users-actions">
                        {entry.status === "Active" ? (
                          <Button
                            aria-label={`Deactivate ${entry.name}`}
                            disabled={isLastActiveAdmin}
                            onClick={() =>
                              requestChange(entry, { status: "Inactive" })
                            }
                            variant="ghost"
                          >
                            <UserRoundX aria-hidden="true" size={15} />
                            Deactivate
                          </Button>
                        ) : (
                          <Button
                            aria-label={`Reactivate ${entry.name}`}
                            onClick={() =>
                              requestChange(entry, { status: "Active" })
                            }
                            variant="ghost"
                          >
                            <RotateCcw aria-hidden="true" size={15} />
                            Reactivate
                          </Button>
                        )}
                        <Button
                          aria-label={`Delete ${entry.name}`}
                          disabled={isSelf || isLastActiveAdmin}
                          onClick={() => requestDelete(entry)}
                          variant="ghost"
                        >
                          <Trash2 aria-hidden="true" size={15} />
                          Delete
                        </Button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <Modal
        description="Create an account. A temporary password will be generated and shown once."
        footer={
          <>
            <Button onClick={closeAdd} variant="secondary">
              Cancel
            </Button>
            <Button
              disabled={
                locationsLoading || Boolean(locationsError) || !locations?.length
              }
              form="add-user-form"
              loading={saving}
              type="submit"
            >
              Add user
            </Button>
          </>
        }
        onClose={closeAdd}
        open={addOpen}
        title="Add user"
      >
        <form className="users-form" id="add-user-form" onSubmit={createUser}>
          <Field label="Name" required>
            <Input
              autoComplete="name"
              onChange={(event) => {
                setName(event.target.value);
                setAddError("");
              }}
              required
              value={name}
            />
          </Field>
          <Field label="Email" required>
            <Input
              autoComplete="email"
              onChange={(event) => {
                setEmail(event.target.value);
                setAddError("");
              }}
              required
              type="email"
              value={email}
            />
          </Field>
          <Field label="Role" required>
            <Select
              onChange={(event) => setRole(event.target.value)}
              value={role}
            >
              <option>User</option>
              <option>Admin</option>
            </Select>
          </Field>
          <Field label="Location" required>
            <Select
              disabled={
                locationsLoading || Boolean(locationsError) || !locations?.length
              }
              onChange={(event) => {
                setLocationId(event.target.value);
                setAddError("");
              }}
              required
              value={locationId}
            >
              <option value="">
                {locationsLoading ? "Loading locations..." : "Select a location"}
              </option>
              {(locations ?? []).map((location) => (
                <option key={location.id} value={location.id}>
                  {location.name} ({location.code})
                </option>
              ))}
            </Select>
          </Field>
          {locationsError && (
            <div className="users-location-error" role="alert">
              <span>{locationsError.message}</span>
              <Button
                onClick={() => void reloadLocations()}
                type="button"
                variant="secondary"
              >
                Try again
              </Button>
            </div>
          )}
          {!locationsLoading && !locationsError && !locations?.length && (
            <p className="users-inline-error" role="status">
              No active locations are available. Add or activate a location
              before creating a user.
            </p>
          )}
          {addError && (
            <p className="users-inline-error" role="alert">
              {addError}
            </p>
          )}
        </form>
      </Modal>

      <Modal
        description="Shown only once. Copy and share this password securely."
        footer={
          <Button onClick={closeCredential} variant="secondary">
            Done
          </Button>
        }
        onClose={closeCredential}
        open={Boolean(credential)}
        title="User created"
      >
        {credential && (
          <div className="users-credential">
            <span className="users-one-time-label">Shown only once</span>
            <div className="users-credential-user">
              <strong>{credential.user.name}</strong>
              <span>{credential.user.email}</span>
            </div>
            <Field label="Temporary password">
              <div className="users-password-row">
                <Input readOnly value={credential.temporaryPassword} />
                <Button
                  aria-label="Copy temporary password"
                  onClick={copyCredential}
                  variant="secondary"
                >
                  {copied ? (
                    <Check aria-hidden="true" size={16} />
                  ) : (
                    <Copy aria-hidden="true" size={16} />
                  )}
                  {copied ? "Copied" : "Copy"}
                </Button>
              </div>
            </Field>
            {copyError && (
              <p className="users-inline-error" role="alert">
                {copyError}
              </p>
            )}
          </div>
        )}
      </Modal>

      <Modal
        description="This permanently removes the account. Users linked to historical records must be deactivated instead."
        footer={
          <>
            <Button disabled={deleting} onClick={closeDelete} variant="secondary">
              Cancel
            </Button>
            <Button
              loading={deleting}
              onClick={confirmDelete}
              variant="destructive"
            >
              Delete user
            </Button>
          </>
        }
        onClose={closeDelete}
        open={Boolean(deleteTarget)}
        title="Delete user?"
      >
        {deleteTarget && (
          <div className="users-delete-confirmation">
            <p>
              Permanently delete <strong>{deleteTarget.name}</strong> (
              {deleteTarget.email})?
            </p>
            {deleteError && (
              <p className="users-inline-error" role="alert">
                {deleteError}
              </p>
            )}
          </div>
        )}
      </Modal>

      <Modal
        description={
          changeTarget?.changes.role
            ? `Change ${changeTarget.user.name}'s role to ${changeTarget.changes.role}?`
            : `${changeTarget?.user.name} will be ${
                changeTarget?.changes.status === "Inactive"
                  ? "unable to sign in"
                  : "able to sign in again"
              }.`
        }
        footer={
          <>
            <Button onClick={closeChange} variant="secondary">
              Cancel
            </Button>
            <Button
              loading={changing}
              onClick={confirmChange}
              variant={
                changeTarget?.changes.status === "Inactive"
                  ? "destructive"
                  : "primary"
              }
            >
              Confirm change
            </Button>
          </>
        }
        onClose={closeChange}
        open={Boolean(changeTarget)}
        title="Confirm user change"
      >
        {changeTarget?.user.role === "Admin" &&
          changeTarget.user.status === "Active" &&
          activeAdminCount <= 1 &&
          (changeTarget.changes.role === "User" ||
            changeTarget.changes.status === "Inactive") && (
            <p className="users-inline-error">
              At least one active administrator must remain.
            </p>
          )}
        {changeError && (
          <p className="users-inline-error" role="alert">
            {changeError}
          </p>
        )}
      </Modal>

      <Toast
        message={toast?.message}
        onClose={() => setToast(null)}
        tone={toast?.tone}
      />
    </section>
  );
}