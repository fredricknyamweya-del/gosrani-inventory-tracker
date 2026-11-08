import { ArrowLeft, Check, Plus, Save } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router";
import AddItemModal from "../components/AddItemModal";
import RequestItemModal from "../components/RequestItemModal";
import {
  Button,
  EmptyState,
  ErrorState,
  Field,
  Input,
  LoadingState,
  PageHeader,
  Select,
  Toast,
} from "../components/ui";
import { useAuth } from "../context/AuthContext";
import { useApi } from "../hooks/useApi";
import { api } from "../services/api";
import { formatDate, todayIso } from "../utils/format";

function makeEntry() {
  return {
    date: todayIso(),
    category: "",
    item: "",
    size: "",
    quantityIn: "",
    quantityOut: "",
    handledBy: "",
    details: "",
  };
}

function validateEntry(entry, item) {
  const errors = {};

  if (!entry.date) errors.date = "Entry date is required.";
  if (!entry.category) errors.category = "Category is required.";
  if (!entry.item) errors.item = "Name of Item is required.";
  if (!entry.handledBy.trim()) {
    errors.handledBy = "Name of the person who handled the stock is required.";
  }
  if (item?.specifications.length && !entry.size) {
    errors.size = "Specifications/Size is required.";
  }
  if (entry.quantityIn === "" && entry.quantityOut === "") {
    errors.quantity = "Enter a value for Quantity In or Quantity Out.";
  }
  for (const key of ["quantityIn", "quantityOut"]) {
    if (
      entry[key] !== "" &&
      (!Number.isInteger(Number(entry[key])) || Number(entry[key]) < 0)
    ) {
      errors[key] = "Use a whole, non-negative number.";
    }
  }

  return errors;
}

export default function EntryFormPage() {
  const { isAdmin } = useAuth();
  const navigate = useNavigate();
  const [entry, setEntry] = useState(makeEntry);
  const [errors, setErrors] = useState({});
  const [stage, setStage] = useState("form");
  const [verified, setVerified] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [pageError, setPageError] = useState(null);
  const [savedEntry, setSavedEntry] = useState(null);
  const [addItemOpen, setAddItemOpen] = useState(false);
  const [requestItemOpen, setRequestItemOpen] = useState(false);
  const [toast, setToast] = useState(null);
  const {
    data: catalog,
    error: catalogError,
    loading: catalogLoading,
    reload: reloadCatalog,
  } = useApi(() => api.getCatalog(), []);
  const {
    data: myRequests,
    error: requestsError,
    loading: requestsLoading,
    reload: reloadMyRequests,
  } = useApi(
    () =>
      isAdmin
        ? Promise.resolve({ data: [] })
        : api.getCatalogRequests(),
    [isAdmin],
  );

  const categories = catalog?.categories ?? [];
  const selectedCategory = categories.find(
    (category) => category.name === entry.category,
  );
  const availableItems = (catalog?.items ?? []).filter(
    (item) => item.active && item.categoryId === selectedCategory?.id,
  );
  const selectedItem = availableItems.find((item) => item.name === entry.item);
  const ownRequests = myRequests ?? [];
  const catalogItems = catalog?.items ?? [];

  useEffect(() => {
    if (!toast) return undefined;
    const timeout = window.setTimeout(() => setToast(null), 4000);
    return () => window.clearTimeout(timeout);
  }, [toast]);

  function update(key, value) {
    setEntry((current) => ({ ...current, [key]: value }));
    setErrors((current) => ({ ...current, [key]: "", quantity: "" }));
  }

  async function handleItemCreated(item) {
    await reloadCatalog();
    setEntry((current) => ({ ...current, item: item.name, size: "" }));
    setErrors((current) => ({ ...current, item: "", size: "" }));
  }

  async function handleRequestCreated() {
    await reloadMyRequests();
    setToast({ message: "Request sent to an administrator" });
  }

  async function review(event) {
    event.preventDefault();
    const nextErrors = validateEntry(entry, selectedItem);
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length) return;

    setSubmitting(true);
    setPageError(null);
    try {
      const response = await api.validateInventory({
        ...entry,
        category: selectedCategory.name,
        item: selectedItem.name,
      });
      setEntry(response.data.rows[0]);
      setStage("review");
      setVerified(false);
    } catch (error) {
      setPageError(error);
    } finally {
      setSubmitting(false);
    }
  }

  async function save() {
    setSubmitting(true);
    setPageError(null);
    try {
      const response = await api.createInventory(entry);
      setSavedEntry(
        Array.isArray(response.data) ? response.data[0] : response.data,
      );
      setStage("success");
    } catch (error) {
      setPageError(error);
    } finally {
      setSubmitting(false);
    }
  }

  if (catalogLoading) {
    return (
      <>
        <PageHeader title="Add inventory entry" />
        <section className="panel entry-form-panel">
          <LoadingState label="Loading product catalog" rows={3} />
        </section>
      </>
    );
  }

  if (catalogError) {
    return (
      <ErrorState
        message={catalogError.message}
        onRetry={reloadCatalog}
        retrying={catalogLoading}
        title="Unable to load product catalog"
      />
    );
  }

  if (stage === "success") {
    return (
      <section className="panel entry-success">
        <span aria-hidden="true" className="entry-success-icon">
          <Check size={22} />
        </span>
        <h1>Inventory entry saved</h1>
        <p>{savedEntry?.item} has been added to the inventory.</p>
        <Link className="btn btn-primary" to="/inventory">
          Back to inventory
        </Link>
      </section>
    );
  }

  if (stage === "review") {
    return (
      <section className="entry-review-page">
        <PageHeader
          className="entry-review-header"
          description="Confirm the entry details before saving."
          eyebrow="Final check"
          title="Review your entry"
        />
        <section className="panel entry-form-panel entry-review-panel">
          <div className="entry-review-banner">
            <span aria-hidden="true" className="entry-review-banner-icon">
              <Check size={18} />
            </span>
            <div>
              <h2>Check everything before saving</h2>
              <p>Review the information below, then confirm it is correct.</p>
            </div>
          </div>
          <dl className="entry-review-list">
            <div>
              <dt>Entry date of the inventory</dt>
              <dd>{entry.date}</dd>
            </div>
            <div>
              <dt>Category</dt>
              <dd>{entry.category}</dd>
            </div>
            <div>
              <dt>Name of Item</dt>
              <dd>{entry.item}</dd>
            </div>
            <div>
              <dt>Specifications/Size</dt>
              <dd>{entry.size || "–"}</dd>
            </div>
            <div>
              <dt>Quantity In</dt>
              <dd>{entry.quantityIn || "–"}</dd>
            </div>
            <div>
              <dt>Quantity Out</dt>
              <dd>{entry.quantityOut || "–"}</dd>
            </div>
            <div>
              <dt>Handled by</dt>
              <dd>{entry.handledBy}</dd>
            </div>
            <div>
              <dt>Description</dt>
              <dd>{entry.details || "–"}</dd>
            </div>
          </dl>
          {pageError && (
            <p className="entry-form-error" role="alert">
              {pageError.message}
            </p>
          )}
          <label className="entry-confirm">
            <input
              checked={verified}
              onChange={(event) => setVerified(event.target.checked)}
              type="checkbox"
            />
            <span>I have verified that this information is correct.</span>
          </label>
          <div className="entry-form-actions">
            <Button
              onClick={() => {
                setStage("form");
                setPageError(null);
              }}
              variant="secondary"
            >
              <ArrowLeft aria-hidden="true" size={17} />
              Edit information
            </Button>
            <Button disabled={!verified} loading={submitting} onClick={save}>
              <Save aria-hidden="true" size={17} />
              Confirm &amp; Save
            </Button>
          </div>
        </section>
      </section>
    );
  }

  return (
    <>
      <PageHeader
        description="Record stock received or issued."
        eyebrow="New inventory record"
        title="Add inventory entry"
      />
      <form className="panel entry-form-panel" onSubmit={review}>
        <div className="entry-form-grid">
          <Field
            error={errors.date}
            label="Entry date of the inventory"
            required
          >
            <Input
              type="date"
              value={entry.date}
              onChange={(event) => update("date", event.target.value)}
            />
          </Field>
          <Field error={errors.category} label="Category" required>
            <Select
              value={entry.category}
              onChange={(event) => {
                setEntry((current) => ({
                  ...current,
                  category: event.target.value,
                  item: "",
                  size: "",
                }));
                setErrors((current) => ({
                  ...current,
                  category: "",
                  item: "",
                  size: "",
                }));
              }}
            >
              <option value="">Select category</option>
              {categories.map((category) => (
                <option key={category.id} value={category.name}>
                  {category.name}
                </option>
              ))}
            </Select>
          </Field>
          <div className="entry-item-field">
            <Field error={errors.item} label="Name of Item" required>
              <Select
                disabled={!entry.category}
                value={entry.item}
                onChange={(event) => {
                  setEntry((current) => ({
                    ...current,
                    item: event.target.value,
                    size: "",
                  }));
                  setErrors((current) => ({
                    ...current,
                    item: "",
                    size: "",
                  }));
                }}
              >
                <option value="">Select item</option>
                {availableItems.map((item) => (
                  <option key={item.id} value={item.name}>
                    {item.name}
                  </option>
                ))}
              </Select>
            </Field>
            {isAdmin ? (
              <Button
                className="entry-catalog-action"
                onClick={() => setAddItemOpen(true)}
                variant="ghost"
              >
                Can't find it? Add a new item
              </Button>
            ) : (
              <Button
                className="entry-catalog-action"
                onClick={() => setRequestItemOpen(true)}
                variant="ghost"
              >
                Can't find it? Request from admin
              </Button>
            )}
          </div>
          <Field
            error={errors.size}
            label="Specifications/Size"
            required={Boolean(selectedItem?.specifications.length)}
          >
            <Select
              disabled={!selectedItem}
              value={entry.size}
              onChange={(event) => update("size", event.target.value)}
            >
              <option value="">Select specifications/size</option>
              {(selectedItem?.specifications ?? []).map((specification) => (
                <option key={specification} value={specification}>
                  {specification}
                </option>
              ))}
            </Select>
          </Field>
          <Field
            error={errors.quantityIn || errors.quantity}
            label="Quantity In"
          >
            <Input
              min="0"
              step="1"
              type="number"
              value={entry.quantityIn ?? ""}
              onChange={(event) => update("quantityIn", event.target.value)}
            />
          </Field>
          <Field
            error={errors.quantityOut || errors.quantity}
            label="Quantity Out"
          >
            <Input
              min="0"
              step="1"
              type="number"
              value={entry.quantityOut ?? ""}
              onChange={(event) => update("quantityOut", event.target.value)}
            />
          </Field>
          <Field error={errors.handledBy} label="Handled by" required>
            <Input
              autoComplete="name"
              maxLength={160}
              onChange={(event) => update("handledBy", event.target.value)}
              placeholder="Name of the person who received or dispatched the stock"
              value={entry.handledBy}
            />
          </Field>
          <Field className="entry-description" label="Description">
            <textarea
              className="input textarea"
              onChange={(event) => update("details", event.target.value)}
              placeholder="Add a description"
              rows="4"
              value={entry.details}
            />
          </Field>
        </div>
        {pageError && (
          <p className="entry-form-error" role="alert">
            {pageError.message}
          </p>
        )}
        <div className="entry-form-actions">
          <Button onClick={() => navigate("/inventory")} variant="secondary">
            Cancel
          </Button>
          <Button loading={submitting} type="submit">
            Review entry
          </Button>
        </div>
      </form>
      {!isAdmin && (
        <section className="panel entry-catalog-request">
          <div>
            <h2>Missing something from the catalog?</h2>
            <p>
              Request a category, product, or specification from an
              administrator.
            </p>
          </div>
          <Button onClick={() => setRequestItemOpen(true)} variant="secondary">
            <Plus aria-hidden="true" size={16} />
            Request catalog addition
          </Button>
        </section>
      )}
      {!isAdmin && (
        <details className="panel entry-own-requests">
          <summary>
            <span>My catalog requests</span>
            <span className="entry-own-request-count">{ownRequests.length}</span>
          </summary>
          {requestsLoading ? (
            <LoadingState label="Loading your item requests" rows={2} />
          ) : requestsError ? (
            <ErrorState
              message={requestsError.message}
              onRetry={reloadMyRequests}
              retrying={requestsLoading}
              title="Unable to load your item requests"
            />
          ) : ownRequests.length === 0 ? (
            <EmptyState
              description="Requests you send will be listed here."
              title="You have no item requests"
            />
          ) : (
            <ul className="entry-own-request-list">
              {ownRequests.map((request) => (
                <li key={request.id}>
                  <div>
                    <strong>
                      {request.requestType === "category"
                        ? request.categoryName
                        : request.itemName}
                    </strong>
                    <span>
                      {[
                        request.requestType,
                        request.category,
                        request.specification,
                      ]
                        .filter(Boolean)
                        .join(" · ")}
                    </span>
                    <time dateTime={request.createdAt}>
                      {formatDate(request.createdAt)}
                    </time>
                  </div>
                  <span
                    className={`entry-own-request-status is-${request.status.toLocaleLowerCase()}`}
                  >
                    {request.status}
                  </span>
                  {request.reason && (
                    <span className="entry-own-request-reason">
                      {request.reason}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </details>
      )}
      {isAdmin ? (
        <AddItemModal
          categories={categories}
          items={catalogItems}
          initialCategoryId={selectedCategory?.id ?? ""}
          onClose={() => setAddItemOpen(false)}
          onCreated={handleItemCreated}
          open={addItemOpen}
        />
      ) : (
        <RequestItemModal
          categories={categories}
          items={catalogItems}
          initialCategoryId={selectedCategory?.id ?? ""}
          initialItemName={entry.item}
          onClose={() => setRequestItemOpen(false)}
          onCreated={handleRequestCreated}
          open={requestItemOpen}
        />
      )}
      <Toast
        message={toast?.message}
        onClose={() => setToast(null)}
        tone={toast?.tone}
      />
    </>
  );
}