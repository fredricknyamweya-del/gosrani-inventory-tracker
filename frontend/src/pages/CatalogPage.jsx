import {
  Check,
  Pencil,
  Plus,
  RotateCcw,
  Search,
  Trash2,
  X,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router";
import AddItemModal from "../components/AddItemModal";
import {
  Button,
  EmptyState,
  ErrorState,
  Field,
  Input,
  LoadingState,
  Modal,
  PageHeader,
  Select,
  Toast,
} from "../components/ui";
import { useApi } from "../hooks/useApi";
import { api } from "../services/api";
import { formatDate } from "../utils/format";

function CatalogStatus({ active }) {
  const status = active ? "Active" : "Inactive";
  return (
    <span
      className={`catalog-item-status${active ? " is-active" : " is-inactive"}`}
    >
      {status}
    </span>
  );
}

function RequestStatus({ request }) {
  return (
    <div className="catalog-request-status">
      <span
        className={`catalog-request-badge is-${request.status.toLocaleLowerCase()}`}
      >
        {request.status}
      </span>
      {request.processedBy && (
        <span className="catalog-reviewer">Reviewed by {request.processedBy}</span>
      )}
    </div>
  );
}

function getRequestType(request) {
  return (
    request.requestType ?? (request.itemId ? "specification" : "product")
  );
}

function getRequestName(request) {
  return getRequestType(request) === "category"
    ? request.categoryName ?? request.category
    : request.itemName;
}

export default function CatalogPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const tabParam = searchParams.get("tab");
  const activeTab = tabParam === "requests" ? "requests" : "catalog";
  const [search, setSearch] = useState("");
  const [categoryOpen, setCategoryOpen] = useState(false);
  const [categoryName, setCategoryName] = useState("");
  const [categoryError, setCategoryError] = useState("");
  const [categorySaving, setCategorySaving] = useState(false);
  const [addItemOpen, setAddItemOpen] = useState(false);
  const [addItemCategoryId, setAddItemCategoryId] = useState("");
  const [renameTarget, setRenameTarget] = useState(null);
  const [renameName, setRenameName] = useState("");
  const [dialogError, setDialogError] = useState("");
  const [dialogSuggestion, setDialogSuggestion] = useState("");
  const [deactivateTarget, setDeactivateTarget] = useState(null);
  const [approveTarget, setApproveTarget] = useState(null);
  const [approveName, setApproveName] = useState("");
  const [rejectTarget, setRejectTarget] = useState(null);
  const [rejectReason, setRejectReason] = useState("");
  const [requestError, setRequestError] = useState("");
  const [requestStatus, setRequestStatus] = useState("Pending");
  const [savingAction, setSavingAction] = useState(false);
  const [busyItemId, setBusyItemId] = useState(null);
  const [specificationItemId, setSpecificationItemId] = useState(null);
  const [specificationDraft, setSpecificationDraft] = useState("");
  const [toast, setToast] = useState(null);

  const {
    data: catalog,
    error: catalogError,
    loading: catalogLoading,
    reload: reloadCatalog,
  } = useApi(() => api.getCatalog(), []);
  const {
    data: requests,
    error: requestsError,
    loading: requestsLoading,
    reload: reloadRequests,
  } = useApi(() => api.getCatalogRequests(), []);

  const categories = catalog?.categories ?? [];
  const items = catalog?.items ?? [];
  const matchingItems = useMemo(() => {
    const query = search.trim().toLocaleLowerCase();
    if (!query) return items;
    return items.filter((item) =>
      `${item.name} ${item.specifications.join(" ")}`
        .toLocaleLowerCase()
        .includes(query),
    );
  }, [items, search]);
  const filteredRequests = (requests ?? []).filter(
    (request) => requestStatus === "All" || request.status === requestStatus,
  );

  useEffect(() => {
    if (tabParam === "catalog" || tabParam === "requests") return;
    const nextParams = new URLSearchParams(searchParams);
    nextParams.set("tab", "catalog");
    setSearchParams(nextParams, { replace: true });
  }, [searchParams, setSearchParams, tabParam]);

  useEffect(() => {
    if (!toast) return undefined;
    const timeout = window.setTimeout(() => setToast(null), 4000);
    return () => window.clearTimeout(timeout);
  }, [toast]);

  const closeCategoryModal = useCallback(() => {
    setCategoryOpen(false);
    setCategoryName("");
    setCategoryError("");
  }, []);

  const closeAddItemModal = useCallback(() => {
    setAddItemOpen(false);
    setAddItemCategoryId("");
  }, []);

  const closeRenameModal = useCallback(() => {
    setRenameTarget(null);
    setRenameName("");
    setDialogError("");
    setDialogSuggestion("");
  }, []);

  const closeDeactivateModal = useCallback(() => {
    setDeactivateTarget(null);
  }, []);

  const closeApproveModal = useCallback(() => {
    setApproveTarget(null);
    setApproveName("");
    setRequestError("");
  }, []);

  const closeRejectModal = useCallback(() => {
    setRejectTarget(null);
    setRejectReason("");
    setRequestError("");
  }, []);

  function selectTab(tab) {
    const nextParams = new URLSearchParams(searchParams);
    nextParams.set("tab", tab);
    setSearchParams(nextParams);
  }

  async function createCategory(event) {
    event.preventDefault();
    setCategorySaving(true);
    setCategoryError("");
    try {
      await api.createCatalogCategory({ name: categoryName });
      await reloadCatalog();
      closeCategoryModal();
      setToast({ message: "Category added to the catalog." });
    } catch (error) {
      setCategoryError(error.message);
    } finally {
      setCategorySaving(false);
    }
  }

  async function handleItemCreated() {
    await reloadCatalog();
    setToast({ message: "Item added to the catalog." });
  }

  async function updateItem(item, changes, successMessage) {
    setBusyItemId(item.id);
    try {
      await api.updateCatalogItem(item.id, changes);
      await reloadCatalog();
      setToast({ message: successMessage });
      setSpecificationItemId(null);
      setSpecificationDraft("");
    } catch (error) {
      setToast({ tone: "error", message: error.message });
    } finally {
      setBusyItemId(null);
    }
  }

  async function saveRename(event) {
    event.preventDefault();
    if (!renameTarget) return;
    setSavingAction(true);
    setDialogError("");
    setDialogSuggestion("");
    try {
      await api.updateCatalogItem(renameTarget.id, { name: renameName });
      await reloadCatalog();
      closeRenameModal();
      setToast({ message: "Item name updated." });
    } catch (error) {
      setDialogError(error.message);
      setDialogSuggestion(error.suggestion ?? "");
    } finally {
      setSavingAction(false);
    }
  }

  async function confirmDeactivation() {
    if (!deactivateTarget) return;
    setSavingAction(true);
    try {
      await api.updateCatalogItem(deactivateTarget.id, { active: false });
      await reloadCatalog();
      closeDeactivateModal();
      setToast({ message: `${deactivateTarget.name} was deactivated.` });
    } catch (error) {
      setToast({ tone: "error", message: error.message });
    } finally {
      setSavingAction(false);
    }
  }

  async function reviewRequest(action) {
    const target = action === "approve" ? approveTarget : rejectTarget;
    if (!target) return;
    setSavingAction(true);
    setRequestError("");
    try {
      await api.updateCatalogRequest(
        target.id,
        action === "approve"
          ? getRequestType(target) === "category"
            ? { action, categoryName: approveName }
            : { action, itemName: approveName }
          : { action, reason: rejectReason },
      );
      await Promise.all([reloadCatalog(), reloadRequests()]);
      if (action === "approve") closeApproveModal();
      else closeRejectModal();
      setToast({
        message:
          action === "approve"
            ? "Request approved and catalog updated."
            : "Request rejected.",
      });
    } catch (error) {
      setRequestError(error.message);
    } finally {
      setSavingAction(false);
    }
  }

  function openRename(item) {
    setRenameTarget(item);
    setRenameName(item.name);
    setDialogError("");
    setDialogSuggestion("");
  }

  function openApproval(request) {
    setApproveTarget(request);
    setApproveName(getRequestName(request));
    setRequestError("");
  }

  function openRejection(request) {
    setRejectTarget(request);
    setRejectReason("");
    setRequestError("");
  }

  return (
    <section className="catalog-page">
      <PageHeader
        description="Manage product categories, items, specifications, and staff requests."
        eyebrow="Administration"
        title="Product catalog"
      />

      <div aria-label="Product catalog sections" className="catalog-tabs" role="tablist">
        <button
          aria-controls="catalog-tab-panel"
          aria-selected={activeTab === "catalog"}
          className={`catalog-tab${activeTab === "catalog" ? " is-active" : ""}`}
          id="catalog-tab"
          onClick={() => selectTab("catalog")}
          role="tab"
          type="button"
        >
          Catalog
        </button>
        <button
          aria-controls="requests-tab-panel"
          aria-selected={activeTab === "requests"}
          className={`catalog-tab${activeTab === "requests" ? " is-active" : ""}`}
          id="requests-tab"
          onClick={() => selectTab("requests")}
          role="tab"
          type="button"
        >
          Requests
          {requests && (
            <span className="catalog-tab-count">
              {requests.filter((request) => request.status === "Pending").length}
            </span>
          )}
        </button>
      </div>

      {activeTab === "catalog" ? (
        <section
          aria-labelledby="catalog-tab"
          className="catalog-tab-panel"
          id="catalog-tab-panel"
          role="tabpanel"
        >
          <div className="catalog-toolbar">
            <label className="catalog-search">
              <Search aria-hidden="true" size={17} />
              <span className="sr-only">Search catalog items</span>
              <Input
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search items or specifications..."
                type="search"
                value={search}
              />
            </label>
            <div className="catalog-toolbar-actions">
              <Button
                onClick={() => setCategoryOpen(true)}
                variant="secondary"
              >
                <Plus aria-hidden="true" size={17} />
                Add category
              </Button>
              <Button
                disabled={categories.length === 0}
                onClick={() => {
                  setAddItemCategoryId("");
                  setAddItemOpen(true);
                }}
              >
                <Plus aria-hidden="true" size={17} />
                Add item
              </Button>
            </div>
          </div>

          {catalogLoading ? (
            <section className="panel">
              <LoadingState label="Loading product catalog" rows={4} />
            </section>
          ) : catalogError ? (
            <ErrorState
              message={catalogError.message}
              onRetry={reloadCatalog}
              retrying={catalogLoading}
              title="Unable to load product catalog"
            />
          ) : categories.length === 0 ? (
            <section className="panel">
              <EmptyState
                action={
                  <Button onClick={() => setCategoryOpen(true)}>
                    <Plus aria-hidden="true" size={17} />
                    Add category
                  </Button>
                }
                description="Create a category before adding catalog items."
                title="No catalog categories"
              />
            </section>
          ) : (
            <div className="catalog-category-list">
              {categories.map((category) => {
                const categoryItems = items.filter(
                  (item) => item.categoryId === category.id,
                );
                const visibleItems = matchingItems.filter(
                  (item) => item.categoryId === category.id,
                );
                if (search.trim() && visibleItems.length === 0) return null;

                return (
                  <section
                    className="panel catalog-category-panel"
                    key={category.id}
                  >
                    <header className="catalog-category-heading">
                      <div>
                        <h2>{category.name}</h2>
                        <span className="catalog-category-count">
                          {categoryItems.length}{" "}
                          {categoryItems.length === 1 ? "item" : "items"}
                        </span>
                      </div>
                      <Button
                        aria-label={`Add item to ${category.name}`}
                        onClick={() => {
                          setAddItemCategoryId(category.id);
                          setAddItemOpen(true);
                        }}
                        variant="secondary"
                      >
                        <Plus aria-hidden="true" size={16} />
                        Add item
                      </Button>
                    </header>

                    {visibleItems.length === 0 ? (
                      <p className="catalog-empty-category">
                        No items in this category yet.
                      </p>
                    ) : (
                      <div className="catalog-item-list">
                        {visibleItems.map((item) => (
                          <article className="catalog-item" key={item.id}>
                            <div className="catalog-item-main">
                              <div className="catalog-item-title">
                                <h3>{item.name}</h3>
                                <CatalogStatus active={item.active} />
                              </div>
                              <div className="catalog-item-actions">
                                <Button
                                  aria-label={`Rename ${item.name}`}
                                  onClick={() => openRename(item)}
                                  variant="ghost"
                                >
                                  <Pencil aria-hidden="true" size={15} />
                                  Rename
                                </Button>
                                {item.active ? (
                                  <Button
                                    aria-label={`Deactivate ${item.name}`}
                                    onClick={() => setDeactivateTarget(item)}
                                    variant="ghost"
                                  >
                                    <X aria-hidden="true" size={16} />
                                    Deactivate
                                  </Button>
                                ) : (
                                  <Button
                                    aria-label={`Reactivate ${item.name}`}
                                    loading={busyItemId === item.id}
                                    onClick={() =>
                                      updateItem(
                                        item,
                                        { active: true },
                                        `${item.name} was reactivated.`,
                                      )
                                    }
                                    variant="ghost"
                                  >
                                    <RotateCcw aria-hidden="true" size={15} />
                                    Reactivate
                                  </Button>
                                )}
                              </div>
                            </div>
                            <div
                              aria-label={`${item.name} specifications`}
                              className="catalog-specification-chips"
                            >
                              {item.specifications.map((specification) => (
                                <span
                                  className="catalog-specification-chip"
                                  key={specification}
                                >
                                  {specification}
                                  <button
                                    aria-label={`Remove ${specification} from ${item.name}`}
                                    disabled={busyItemId === item.id}
                                    onClick={() =>
                                      updateItem(
                                        item,
                                        { removeSpecifications: [specification] },
                                        `${specification} was removed.`,
                                      )
                                    }
                                    type="button"
                                  >
                                    <X aria-hidden="true" size={13} />
                                  </button>
                                </span>
                              ))}
                              {item.specifications.length === 0 && (
                                <span className="catalog-empty-specifications">
                                  No specifications
                                </span>
                              )}
                            </div>
                            {specificationItemId === item.id ? (
                              <form
                                className="catalog-add-specification"
                                onSubmit={(event) => {
                                  event.preventDefault();
                                  if (!specificationDraft.trim()) return;
                                  void updateItem(
                                    item,
                                    { addSpecifications: [specificationDraft] },
                                    "Specification added.",
                                  );
                                }}
                              >
                                <Input
                                  aria-label={`New specification for ${item.name}`}
                                  autoFocus
                                  onChange={(event) =>
                                    setSpecificationDraft(event.target.value)
                                  }
                                  placeholder="New specification"
                                  value={specificationDraft}
                                />
                                <Button
                                  aria-label="Save specification"
                                  loading={busyItemId === item.id}
                                  type="submit"
                                >
                                  <Check aria-hidden="true" size={16} />
                                  Save
                                </Button>
                                <Button
                                  aria-label="Cancel adding specification"
                                  onClick={() => {
                                    setSpecificationItemId(null);
                                    setSpecificationDraft("");
                                  }}
                                  variant="secondary"
                                >
                                  Cancel
                                </Button>
                              </form>
                            ) : (
                              <Button
                                className="catalog-add-specification-trigger"
                                onClick={() => {
                                  setSpecificationItemId(item.id);
                                  setSpecificationDraft("");
                                }}
                                variant="ghost"
                              >
                                <Plus aria-hidden="true" size={15} />
                                Add specification
                              </Button>
                            )}
                          </article>
                        ))}
                      </div>
                    )}
                  </section>
                );
              })}
              {search.trim() && matchingItems.length === 0 && (
                <section className="panel">
                  <EmptyState
                    description="Try another item name or specification."
                    title="No matching catalog items"
                  />
                </section>
              )}
            </div>
          )}
        </section>
      ) : (
        <section
          aria-labelledby="requests-tab"
          className="catalog-tab-panel"
          id="requests-tab-panel"
          role="tabpanel"
        >
          <div className="catalog-toolbar catalog-request-toolbar">
            <p>
              Review staff requests for missing categories, products, or
              specifications.
            </p>
            <label className="catalog-status-filter">
              <span>Filter by status</span>
              <Select
                aria-label="Filter requests by status"
                onChange={(event) => setRequestStatus(event.target.value)}
                value={requestStatus}
              >
                <option>Pending</option>
                <option>Approved</option>
                <option>Rejected</option>
                <option>All</option>
              </Select>
            </label>
          </div>
          {requestsLoading ? (
            <section className="panel">
              <LoadingState label="Loading catalog requests" rows={4} />
            </section>
          ) : requestsError ? (
            <ErrorState
              message={requestsError.message}
              onRetry={reloadRequests}
              retrying={requestsLoading}
              title="Unable to load catalog requests"
            />
          ) : filteredRequests.length === 0 ? (
            <section className="panel">
              <EmptyState
                description={
                  requestStatus === "Pending"
                    ? "Staff requests will appear here for review."
                    : `There are no ${requestStatus.toLocaleLowerCase()} requests.`
                }
                title={
                  requestStatus === "Pending"
                    ? "No pending requests"
                    : `No ${requestStatus.toLocaleLowerCase()} requests`
                }
              />
            </section>
          ) : (
            <div className="panel table-scroll">
              <table className="data-table catalog-request-table">
                <thead>
                  <tr>
                    <th scope="col">Requested by</th>
                    <th scope="col">Type</th>
                    <th scope="col">Category</th>
                    <th scope="col">Item</th>
                    <th scope="col">Specification</th>
                    <th scope="col">Note</th>
                    <th scope="col">Date</th>
                    <th scope="col">Status</th>
                    <th scope="col">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredRequests.map((request) => (
                    <tr key={request.id}>
                      <td>{request.requestedBy}</td>
                      <td>
                        {getRequestType(request)[0].toLocaleUpperCase()}
                        {getRequestType(request).slice(1)}
                      </td>
                      <td>
                        {request.categoryName ?? request.category ?? "–"}
                      </td>
                      <td>
                        {getRequestType(request) === "category"
                          ? "–"
                          : request.itemName}
                      </td>
                      <td>{request.specification || "–"}</td>
                      <td>{request.note || "–"}</td>
                      <td>{formatDate(request.createdAt)}</td>
                      <td>
                        <RequestStatus request={request} />
                        {request.reason && (
                          <span className="catalog-reviewer">
                            Reason: {request.reason}
                          </span>
                        )}
                      </td>
                      <td>
                        {request.status === "Pending" ? (
                          <div className="catalog-request-actions">
                            <Button
                              aria-label={`Approve ${getRequestName(request)} request`}
                              onClick={() => openApproval(request)}
                              variant="secondary"
                            >
                              <Check aria-hidden="true" size={15} />
                              Approve
                            </Button>
                            <Button
                              aria-label={`Reject ${getRequestName(request)} request`}
                              onClick={() => openRejection(request)}
                              variant="ghost"
                            >
                              <X aria-hidden="true" size={15} />
                              Reject
                            </Button>
                          </div>
                        ) : (
                          <span className="catalog-reviewed">Reviewed</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      <Modal
        description="Categories help organize catalog items for inventory entries."
        footer={
          <>
            <Button onClick={closeCategoryModal} variant="secondary">
              Cancel
            </Button>
            <Button
              form="add-catalog-category-form"
              loading={categorySaving}
              type="submit"
            >
              Add category
            </Button>
          </>
        }
        onClose={closeCategoryModal}
        open={categoryOpen}
        title="Add category"
      >
        <form
          className="catalog-dialog-form"
          id="add-catalog-category-form"
          onSubmit={createCategory}
        >
          <Field label="Category name" required>
            <Input
              autoComplete="off"
              onChange={(event) => {
                setCategoryName(event.target.value);
                setCategoryError("");
              }}
              value={categoryName}
            />
          </Field>
          {categoryError && (
            <p className="catalog-inline-error" role="alert">
              {categoryError}
            </p>
          )}
        </form>
      </Modal>

      <AddItemModal
        categories={categories}
        initialCategoryId={addItemCategoryId}
        onClose={closeAddItemModal}
        onCreated={handleItemCreated}
        open={addItemOpen}
      />

      <Modal
        description="Update the item name. Names must be unique within a category."
        footer={
          <>
            <Button onClick={closeRenameModal} variant="secondary">
              Cancel
            </Button>
            <Button
              form="rename-catalog-item-form"
              loading={savingAction}
              type="submit"
            >
              Save name
            </Button>
          </>
        }
        onClose={closeRenameModal}
        open={Boolean(renameTarget)}
        title="Rename item"
      >
        <form
          className="catalog-dialog-form"
          id="rename-catalog-item-form"
          onSubmit={saveRename}
        >
          <Field label="Item name" required>
            <Input
              autoComplete="off"
              onChange={(event) => setRenameName(event.target.value)}
              value={renameName}
            />
          </Field>
          {dialogError && (
            <p className="catalog-inline-error" role="alert">
              {dialogError}
            </p>
          )}
          {dialogSuggestion && (
            <p className="catalog-hint">Did you mean {dialogSuggestion}?</p>
          )}
        </form>
      </Modal>

      <Modal
        description="Deactivated items will no longer be offered for new entries. Existing inventory records are not affected."
        footer={
          <>
            <Button onClick={closeDeactivateModal} variant="secondary">
              Cancel
            </Button>
            <Button
              loading={savingAction}
              onClick={confirmDeactivation}
              variant="destructive"
            >
              <Trash2 aria-hidden="true" size={16} />
              Deactivate item
            </Button>
          </>
        }
        onClose={closeDeactivateModal}
        open={Boolean(deactivateTarget)}
        title={`Deactivate ${deactivateTarget?.name ?? "item"}?`}
      >
        <p>
          This item will be hidden from new entries. Existing inventory records
          are not affected.
        </p>
      </Modal>

      <Modal
        description={
          getRequestType(approveTarget ?? {}) === "category"
            ? "Add the requested category to the catalog."
            : `${approveTarget?.category ?? ""} · ${approveTarget?.specification ?? ""}`
        }
        footer={
          <>
            <Button onClick={closeApproveModal} variant="secondary">
              Cancel
            </Button>
            <Button
              disabled={!approveName.trim()}
              loading={savingAction}
              onClick={() => reviewRequest("approve")}
            >
              <Check aria-hidden="true" size={16} />
              Approve request
            </Button>
          </>
        }
        onClose={closeApproveModal}
        open={Boolean(approveTarget)}
        title="Approve catalog request"
      >
        <p>
          {getRequestType(approveTarget ?? {}) === "category"
            ? "Approving adds this category to the catalog."
            : getRequestType(approveTarget ?? {}) === "product"
              ? "Approving adds the requested product and its initial specification."
              : "Approving adds the requested specification to this product."}
        </p>
        <Field
          label={
            getRequestType(approveTarget ?? {}) === "category"
              ? "Category name"
              : "Item name"
          }
          required
        >
          <Input
            autoComplete="off"
            onChange={(event) => setApproveName(event.target.value)}
            value={approveName}
          />
        </Field>
        {requestError && (
          <p className="catalog-inline-error" role="alert">
            {requestError}
          </p>
        )}
      </Modal>

      <Modal
        description={
          getRequestType(rejectTarget ?? {}) === "category"
            ? getRequestName(rejectTarget ?? {})
            : `${getRequestName(rejectTarget ?? {}) ?? ""} · ${rejectTarget?.specification ?? ""}`
        }
        footer={
          <>
            <Button onClick={closeRejectModal} variant="secondary">
              Cancel
            </Button>
            <Button
              loading={savingAction}
              onClick={() => reviewRequest("reject")}
              variant="destructive"
            >
              Reject request
            </Button>
          </>
        }
        onClose={closeRejectModal}
        open={Boolean(rejectTarget)}
        title="Reject catalog request"
      >
        <Field
          hint="Optional — add a short reason for the requester."
          label="Reason"
        >
          <textarea
            className="input textarea"
            onChange={(event) => setRejectReason(event.target.value)}
            rows={3}
            value={rejectReason}
          />
        </Field>
        {requestError && (
          <p className="catalog-inline-error" role="alert">
            {requestError}
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
