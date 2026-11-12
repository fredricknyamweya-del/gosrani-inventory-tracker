import {
  ChevronLeft,
  ChevronRight,
  LockKeyhole,
  Pencil,
  Search,
  Trash2,
  X,
} from "lucide-react";
import { Link, useSearchParams } from "react-router";
import { useEffect, useState } from "react";
import {
  Button,
  EmptyState,
  ErrorState,
  Input,
  LoadingState,
  Modal,
  PageHeader,
  Select,
  StatusBadge,
  Toast,
} from "../components/ui";
import { useApi } from "../hooks/useApi";
import { useAuth } from "../context/AuthContext";
import { formatDate } from "../utils/format";
import { api } from "../services/api";

const PAGE_SIZE = 5;

export default function InventoryPage() {
  const { isAdmin } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const urlSearch = searchParams.get("search") ?? "";
  const [search, setSearch] = useState(urlSearch);
  const [category, setCategory] = useState("");
  const [item, setItem] = useState("");
  const [size, setSize] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [sort, setSort] = useState("desc");
  const [page, setPage] = useState(1);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [toast, setToast] = useState(null);

  const {
    data: records,
    meta,
    error: inventoryError,
    loading: inventoryLoading,
    reload: reloadInventory,
  } = useApi(
    () =>
      api.getInventory({
        search: search.trim(),
        category,
        item,
        size,
        from,
        to,
        sort,
        page,
        limit: PAGE_SIZE,
      }),
    [search, category, item, size, from, to, sort, page],
  );
  const {
    data: catalog,
    error: catalogError,
    loading: catalogLoading,
    reload: reloadCatalog,
  } = useApi(() => api.getCatalog(), []);

  const categories = catalog?.categories ?? [];
  const selectedCategory = categories.find((entry) => entry.name === category);
  const availableItems = (catalog?.items ?? []).filter(
    (entry) => entry.active && entry.categoryId === selectedCategory?.id,
  );
  const selectedItem = availableItems.find((entry) => entry.name === item);
  const availableSizes = selectedItem?.specifications ?? [];
  const totalPages = Math.max(1, meta?.pages ?? 1);
  const hasFilters = Boolean(search.trim() || category || item || size || from || to);

  useEffect(() => {
    setSearch(urlSearch);
    setPage(1);
  }, [urlSearch]);

  useEffect(() => {
    if (!inventoryLoading && page > totalPages) setPage(totalPages);
  }, [inventoryLoading, page, totalPages]);

  useEffect(() => {
    if (!toast) return undefined;
    const timeout = window.setTimeout(() => setToast(null), 4000);
    return () => window.clearTimeout(timeout);
  }, [toast]);

  function updateSearch(value) {
    setSearch(value);
    setPage(1);
    const nextParams = new URLSearchParams(searchParams);
    if (value.trim()) nextParams.set("search", value);
    else nextParams.delete("search");
    setSearchParams(nextParams, { replace: true });
  }

  function clearFilters() {
    setCategory("");
    setItem("");
    setSize("");
    setFrom("");
    setTo("");
    setSort("desc");
    updateSearch("");
  }

  function changeCategory(value) {
    setCategory(value);
    setItem("");
    setSize("");
    setPage(1);
  }

  function changeItem(value) {
    setItem(value);
    setSize("");
    setPage(1);
  }

  async function confirmDelete() {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await api.deleteInventory(deleteTarget.id);
      setDeleteTarget(null);
      setToast({ message: "Inventory record deleted." });
      await reloadInventory();
    } catch (error) {
      setToast({
        tone: "error",
        message: error.message || "Unable to delete this inventory record.",
      });
    } finally {
      setDeleting(false);
    }
  }

  const requestError = inventoryError ?? catalogError;

  return (
    <section className="inventory-page">
      <PageHeader
        actions={
          <Link className="btn btn-primary" to="/inventory/new">
            Add entry
          </Link>
        }
        description="Review inventory movements and narrow the list with filters."
        eyebrow="Gosrani Wholesalers Limited"
        title="Inventory"
      />

      <section aria-label="Inventory filters" className="panel inventory-filters">
        <div className="inventory-search-field">
          <label className="sr-only" htmlFor="inventory-search">
            Search inventory
          </label>
          <Search aria-hidden="true" size={17} />
          <Input
            autoComplete="off"
            id="inventory-search"
            onChange={(event) => updateSearch(event.target.value)}
            placeholder="Search item, details, or staff..."
            type="search"
            value={search}
          />
        </div>
        <label className="inventory-filter">
          <span>Category</span>
          <Select
            aria-label="Filter by category"
            onChange={(event) => changeCategory(event.target.value)}
            value={category}
          >
            <option value="">All categories</option>
            {categories.map((entry) => (
              <option key={entry.id} value={entry.name}>
                {entry.name}
              </option>
            ))}
          </Select>
        </label>
        <label className="inventory-filter">
          <span>Item</span>
          <Select
            aria-label="Filter by item"
            disabled={!category || catalogLoading}
            onChange={(event) => changeItem(event.target.value)}
            value={item}
          >
            <option value="">All items</option>
            {availableItems.map((entry) => (
              <option key={entry.id} value={entry.name}>
                {entry.name}
              </option>
            ))}
          </Select>
        </label>
        <label className="inventory-filter">
          <span>Date from</span>
          <Input
            aria-label="Filter from date"
            max={to || undefined}
            onChange={(event) => {
              setFrom(event.target.value);
              setPage(1);
            }}
            type="date"
            value={from}
          />
        </label>
        <label className="inventory-filter">
          <span>Date to</span>
          <Input
            aria-label="Filter to date"
            min={from || undefined}
            onChange={(event) => {
              setTo(event.target.value);
              setPage(1);
            }}
            type="date"
            value={to}
          />
        </label>
        <label className="inventory-filter">
          <span>Size / Specifications</span>
          <Select
            aria-label="Filter by size or specification"
            disabled={!item || catalogLoading}
            onChange={(event) => {
              setSize(event.target.value);
              setPage(1);
            }}
            value={size}
          >
            <option value="">All sizes</option>
            {availableSizes.map((specification) => (
              <option key={specification} value={specification}>
                {specification}
              </option>
            ))}
          </Select>
        </label>
        <label className="inventory-filter">
          <span>Sort by date</span>
          <Select
            aria-label="Sort by date"
            onChange={(event) => {
              setSort(event.target.value);
              setPage(1);
            }}
            value={sort}
          >
            <option value="desc">Newest first</option>
            <option value="asc">Oldest first</option>
          </Select>
        </label>
        {hasFilters && (
          <Button
            className="inventory-clear-filters"
            onClick={clearFilters}
            variant="ghost"
          >
            <X aria-hidden="true" size={15} />
            Clear filters
          </Button>
        )}
      </section>

      {requestError ? (
        <ErrorState
          message={requestError.message}
          onRetry={() => {
            void reloadInventory();
            void reloadCatalog();
          }}
          retrying={inventoryLoading || catalogLoading}
          title="Unable to load inventory"
        />
      ) : (
        <section aria-label="Inventory records" className="panel inventory-table-panel">
          {inventoryLoading || catalogLoading ? (
            <LoadingState label="Loading inventory records" rows={5} />
          ) : records?.length ? (
            <>
              <div className="table-scroll">
                <table className="data-table inventory-table">
                  <thead>
                    <tr>
                      <th scope="col">Date</th>
                      <th scope="col">Category</th>
                      <th scope="col">Item</th>
                      <th scope="col">Size / Specifications</th>
                      <th scope="col">Qty In</th>
                      <th scope="col">Qty Out</th>
                      <th scope="col">Inventory Details</th>
                      <th scope="col">Received / Dispatched By</th>
                      <th scope="col">Added By</th>
                      <th scope="col">Status</th>
                      {isAdmin && <th scope="col">Actions</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {records.map((record) => (
                      <tr key={record.id}>
                        <td>{formatDate(record.date)}</td>
                        <td>{record.category}</td>
                        <td>
                          <Link
                            aria-label={`View ${record.item} inventory record`}
                            className="inventory-record-link"
                            to={`/inventory/${encodeURIComponent(record.id)}`}
                          >
                            {record.item}
                          </Link>
                        </td>
                        <td>{record.size || "–"}</td>
                        <td>
                          {record.quantityIn ?? "–"}{" "}
                          <small>{record.enteredUnit}</small>
                        </td>
                        <td>
                          {record.quantityOut ?? "–"}{" "}
                          <small>{record.enteredUnit}</small>
                        </td>
                        <td className="inventory-details-cell" title={record.details || undefined}>
                          {record.details || "–"}
                        </td>
                        <td>{record.handledBy || "–"}</td>
                        <td>{record.addedBy || "–"}</td>
                        <td>
                          <span className="inventory-status-cell">
                            {!isAdmin && record.status === "Locked" && (
                              <LockKeyhole
                                aria-label="Locked record"
                                className="inventory-lock-icon"
                                size={14}
                              />
                            )}
                            <StatusBadge status={record.status} />
                          </span>
                        </td>
                        {isAdmin && (
                          <td>
                            <div className="inventory-row-actions">
                              <Link
                                aria-label={`Edit ${record.item} inventory record`}
                                className="icon-btn inventory-edit-action"
                                to={`/inventory/${encodeURIComponent(record.id)}?edit=true`}
                              >
                                <Pencil aria-hidden="true" size={16} />
                              </Link>
                              <button
                                aria-label={`Delete ${record.item} inventory record`}
                                className="icon-btn inventory-delete-action"
                                onClick={() => setDeleteTarget(record)}
                                type="button"
                              >
                                <Trash2 aria-hidden="true" size={16} />
                              </button>
                            </div>
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <nav aria-label="Inventory pagination" className="inventory-pagination">
                <span>
                  Page {meta?.page ?? page} of {totalPages}
                </span>
                <div>
                  <Button
                    aria-label="Previous page"
                    disabled={page <= 1}
                    onClick={() => setPage((current) => Math.max(1, current - 1))}
                    variant="secondary"
                  >
                    <ChevronLeft aria-hidden="true" size={16} />
                    Previous
                  </Button>
                  <Button
                    aria-label="Next page"
                    disabled={page >= totalPages}
                    onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
                    variant="secondary"
                  >
                    Next
                    <ChevronRight aria-hidden="true" size={16} />
                  </Button>
                </div>
              </nav>
            </>
          ) : (
            <EmptyState
              action={
                hasFilters ? (
                  <Button onClick={clearFilters} variant="secondary">
                    Clear filters
                  </Button>
                ) : (
                  <Link className="btn btn-primary" to="/inventory/new">
                    Add first entry
                  </Link>
                )
              }
              description={
                hasFilters
                  ? "Try changing or clearing your filters."
                  : "Inventory entries will appear here once they are added."
              }
              title={hasFilters ? "No matching records" : "No inventory records yet"}
            />
          )}
        </section>
      )}

      <Modal
        description="This removes the inventory record. This action cannot be undone."
        footer={
          <>
            <Button
              disabled={deleting}
              onClick={() => setDeleteTarget(null)}
              variant="secondary"
            >
              Cancel
            </Button>
            <Button
              loading={deleting}
              onClick={confirmDelete}
              variant="destructive"
            >
              Delete record
            </Button>
          </>
        }
        onClose={() => {
          if (!deleting) setDeleteTarget(null);
        }}
        open={Boolean(deleteTarget)}
        title="Delete inventory record?"
      >
        {deleteTarget && (
          <p>
            Delete <strong>{deleteTarget.item}</strong> from{" "}
            {formatDate(deleteTarget.date)}?
          </p>
        )}
      </Modal>
      <div aria-live="polite" className="toast-container">
        <Toast
          message={toast?.message}
          onClose={() => setToast(null)}
          tone={toast?.tone}
        />
      </div>
    </section>
  );
}