import { ArrowLeft, Check, Plus, Save, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router";
import AddItemModal from "../components/AddItemModal";
import QuantityDisplay from "../components/QuantityDisplay";
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
import { calculateTotalPieces } from "../utils/units";

function makeEntry(id) {
  return {
    id,
    date: todayIso(),
    category: "",
    item: "",
    size: "",
    enteredUnit: "PCS",
    piecesPerBale: "",
    quantityIn: "",
    quantityOut: "",
    handledBy: "",
    details: "",
  };
}

function unitLabel(unit, plural = true) {
  if (unit === "BALE") return plural ? "bales" : "bale";
  if (unit === "KG") return "kg";
  return plural ? "pcs" : "pc";
}

function validateEntry(entry, item) {
  const errors = {};
  const allowsFractionalQuantity = entry.enteredUnit === "KG";

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
  if (entry.enteredUnit === "BALE") {
    const piecesPerBale = Number(entry.piecesPerBale);
    if (
      !Number.isInteger(piecesPerBale) ||
      piecesPerBale < 1 ||
      piecesPerBale > 10_000
    ) {
      errors.piecesPerBale =
        "Enter a whole number from 1 to 10000 pieces per bale.";
    }
  }
  for (const key of ["quantityIn", "quantityOut"]) {
    if (entry[key] === "") continue;
    const quantity = Number(entry[key]);
    const fractionalDigits =
      entry[key].split(".")[1]?.replace(/0+$/, "").length ?? 0;
    if (
      !Number.isFinite(quantity) ||
      quantity < 0 ||
      (allowsFractionalQuantity
        ? !/^(?:\d+(?:\.\d*)?|\.\d+)$/.test(entry[key]) ||
          fractionalDigits > 3
        : !Number.isInteger(quantity))
    ) {
      errors[key] = allowsFractionalQuantity
        ? "Use a non-negative number with no more than 3 decimal places."
        : "Use a whole, non-negative number.";
    }
  }

  return errors;
}

export default function EntryFormPage() {
  const { isAdmin } = useAuth();
  const navigate = useNavigate();
  const entryId = useRef(0);
  const [entries, setEntries] = useState(() => [
    makeEntry(++entryId.current),
  ]);
  const [errors, setErrors] = useState({});
  const [reviewWarnings, setReviewWarnings] = useState([]);
  const [stage, setStage] = useState("form");
  const [verified, setVerified] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [pageError, setPageError] = useState(null);
  const [savedEntries, setSavedEntries] = useState([]);
  const [addItemEntryId, setAddItemEntryId] = useState(null);
  const [requestItemEntryId, setRequestItemEntryId] = useState(null);
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
  const ownRequests = myRequests ?? [];
  const catalogItems = catalog?.items ?? [];
  const activeAddItemEntry = entries.find(
    (entry) => entry.id === addItemEntryId,
  );
  const activeRequestItemEntry = entries.find(
    (entry) => entry.id === requestItemEntryId,
  );

  useEffect(() => {
    if (!toast) return undefined;
    const timeout = window.setTimeout(() => setToast(null), 4000);
    return () => window.clearTimeout(timeout);
  }, [toast]);

  function updateEntry(entryId, key, value) {
    setEntries((current) =>
      current.map((entry) =>
        entry.id === entryId ? { ...entry, [key]: value } : entry,
      ),
    );
    setErrors((current) => ({
      ...current,
      [entryId]: {
        ...current[entryId],
        [key]: "",
        quantity: "",
      },
    }));
  }

  function addEntry() {
    const newEntry = makeEntry(++entryId.current);
    setEntries((current) => [...current, newEntry]);
  }

  function removeEntry(entryId) {
    setEntries((current) => current.filter((entry) => entry.id !== entryId));
    setErrors((current) => {
      const next = { ...current };
      delete next[entryId];
      return next;
    });
  }

  async function handleItemCreated(item) {
    await reloadCatalog();
    if (!activeAddItemEntry) return;
    setEntries((current) =>
      current.map((entry) =>
        entry.id === activeAddItemEntry.id
          ? {
              ...entry,
              category:
                categories.find(
                  (category) => category.id === item.categoryId,
                )?.name ?? entry.category,
              item: item.name,
              enteredUnit: item.entryUnit ?? "PCS",
              piecesPerBale: "",
              size: "",
            }
          : entry,
      ),
    );
    setErrors((current) => ({
      ...current,
      [activeAddItemEntry.id]: {
        ...current[activeAddItemEntry.id],
        category: "",
        item: "",
        size: "",
      },
    }));
  }

  async function handleRequestCreated() {
    await reloadMyRequests();
    setToast({ message: "Request sent to an administrator" });
  }

  async function review(event) {
    event.preventDefault();
    const nextErrors = {};
    for (const entry of entries) {
      const category = categories.find(
        (candidate) => candidate.name === entry.category,
      );
      const selectedItem = catalogItems.find(
        (item) =>
          item.active &&
          item.categoryId === category?.id &&
          item.name === entry.item,
      );
      const entryErrors = validateEntry(entry, selectedItem);
      if (!category) {
        entryErrors.category = "Choose a category from the catalog.";
      }
      if (entry.item && !selectedItem) {
        entryErrors.item = "Choose an item from the selected category.";
      }
      if (Object.keys(entryErrors).length) {
        nextErrors[entry.id] = entryErrors;
      }
    }
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length) return;

    setSubmitting(true);
    setPageError(null);
    try {
      const payload = entries.map(({ id, ...entry }) => {
        const category = categories.find(
          (candidate) => candidate.name === entry.category,
        );
        const selectedItem = catalogItems.find(
          (item) =>
            item.active &&
            item.categoryId === category?.id &&
            item.name === entry.item,
        );
        return {
          ...entry,
          category: category.name,
          item: selectedItem.name,
        };
      });
      const response = await api.validateInventory(payload);
      setEntries((current) =>
        current.map((entry, index) => ({
          ...entry,
          ...response.data.rows[index],
        })),
      );
      setReviewWarnings(response.data.warnings ?? []);
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
      const payload = entries.map(({ id, ...entry }) => entry);
      const response = await api.createInventory(payload);
      setSavedEntries(
        Array.isArray(response.data) ? response.data : [response.data],
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
        <h1>
          {savedEntries.length === 1
            ? "Inventory entry saved"
            : "Inventory entries saved"}
        </h1>
        <p>
          {savedEntries.length === 1
            ? `${savedEntries[0].item} has been added to the inventory.`
            : `${savedEntries.length} entries have been added to the inventory.`}
        </p>
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
          description="Confirm all entry details before saving."
          eyebrow="Final check"
          title="Review your entries"
        />
        <section className="panel entry-form-panel entry-review-panel">
          <div className="entry-review-banner">
            <span aria-hidden="true" className="entry-review-banner-icon">
              <Check size={18} />
            </span>
            <div>
              <h2>Check all entries before saving</h2>
              <p>
                Review each of the {entries.length} entries, then confirm they
                are correct.
              </p>
            </div>
          </div>
          <ol className="entry-review-entries">
            {entries.map((entry, index) => {
              const enteredUnitLabel = unitLabel(entry.enteredUnit);
                const entryWarning = reviewWarnings.find(
                  (warning) => warning.index === index,
                );
              return (
                <li className="entry-review-card" key={entry.id}>
                  <h3>Entry {index + 1}</h3>
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
                      <dd>
                        <QuantityDisplay
                          display={entry.quantityInDisplay}
                          secondary={entry.quantityInSecondaryDisplay}
                        />
                      </dd>
                    </div>
                    <div>
                      <dt>Quantity Out</dt>
                      <dd>
                        <QuantityDisplay
                          display={entry.quantityOutDisplay}
                          secondary={entry.quantityOutSecondaryDisplay}
                        />
                      </dd>
                    </div>
                    {entry.enteredUnit === "BALE" && (
                      <div>
                        <dt>Bale contents</dt>
                        <dd>
                          {entry.piecesPerBale} pcs per bale
                          {entry.piecesPerBale !== entry.packSize &&
                            entry.packSize != null && (
                              <small className="entry-standard-warning">
                                Catalogue standard: {entry.packSize} pcs
                              </small>
                            )}
                        </dd>
                      </div>
                    )}
                    <div>
                      <dt>Entered unit</dt>
                      <dd>{enteredUnitLabel}</dd>
                    </div>
                    <div>
                      <dt>Received / dispatched by</dt>
                      <dd>{entry.handledBy}</dd>
                    </div>
                    <div>
                      <dt>Description</dt>
                      <dd>{entry.details || "–"}</dd>
                    </div>
                  </dl>
                  {entryWarning?.flags?.length > 0 && (
                    <ul className="entry-review-warnings">
                      {entryWarning.flags.map((warning) => (
                        <li key={`${warning.field}-${warning.message}`}>
                          {warning.message}
                        </li>
                      ))}
                    </ul>
                  )}
                </li>
              );
            })}
          </ol>
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
              Confirm &amp; Save {entries.length === 1 ? "Entry" : "Entries"}
            </Button>
          </div>
        </section>
      </section>
    );
  }

  return (
    <>
      <PageHeader
        description="Add one or more inventory entries at once."
        eyebrow="New inventory record"
        title="Add inventory entries"
      />
      <form className="panel entry-form-panel" onSubmit={review}>
        <div className="entry-batch-list">
          {entries.map((entry, index) => {
            const entryErrors = errors[entry.id] ?? {};
            const selectedCategory = categories.find(
              (category) => category.name === entry.category,
            );
            const availableItems = catalogItems.filter(
              (item) =>
                item.active && item.categoryId === selectedCategory?.id,
            );
            const selectedItem = availableItems.find(
              (item) => item.name === entry.item,
            );
            const enteredUnitLabel = unitLabel(entry.enteredUnit);
            const selectedSpecification = selectedItem?.specificationPackSizes?.find(
              (specification) => specification.label === entry.size,
            );
            const packSize = selectedSpecification?.packSize ?? null;
            const isBaleUnit = entry.enteredUnit === "BALE";
            const quantityStep = entry.enteredUnit === "KG" ? "0.001" : "1";
            const totalPiecesIn = calculateTotalPieces(
              entry.quantityIn,
              entry.piecesPerBale,
            );
            const totalPiecesOut = calculateTotalPieces(
              entry.quantityOut,
              entry.piecesPerBale,
            );

            return (
              <section className="entry-batch-row" key={entry.id}>
                <div className="entry-batch-heading">
                  <h2>Entry {index + 1}</h2>
                  {entries.length > 1 && (
                    <Button
                      aria-label={`Remove entry ${index + 1}`}
                      className="entry-remove-row"
                      onClick={() => removeEntry(entry.id)}
                      variant="ghost"
                    >
                      <X aria-hidden="true" size={16} />
                      Remove
                    </Button>
                  )}
                </div>
                <div className="entry-form-grid">
                  <Field
                    error={entryErrors.date}
                    label="Entry date of the inventory"
                    required
                  >
                    <Input
                      type="date"
                      value={entry.date}
                      onChange={(event) =>
                        updateEntry(entry.id, "date", event.target.value)
                      }
                    />
                  </Field>
                  <Field
                    error={entryErrors.category}
                    label="Category"
                    required
                  >
                    <Select
                      value={entry.category}
                      onChange={(event) => {
                        updateEntry(
                          entry.id,
                          "category",
                          event.target.value,
                        );
                        updateEntry(entry.id, "item", "");
                        updateEntry(entry.id, "size", "");
                        updateEntry(entry.id, "enteredUnit", "PCS");
                        updateEntry(entry.id, "piecesPerBale", "");
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
                    <Field
                      error={entryErrors.item}
                      label="Name of Item"
                      required
                    >
                      <Select
                        disabled={!entry.category}
                        value={entry.item}
                        onChange={(event) => {
                          const nextItem = availableItems.find(
                            (item) => item.name === event.target.value,
                          );
                          updateEntry(entry.id, "item", event.target.value);
                          updateEntry(
                            entry.id,
                            "enteredUnit",
                            nextItem?.entryUnit ?? "PCS",
                          );
                          updateEntry(entry.id, "size", "");
                          updateEntry(entry.id, "piecesPerBale", "");
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
                        onClick={() => setAddItemEntryId(entry.id)}
                        variant="ghost"
                      >
                        Can't find it? Add a new item
                      </Button>
                    ) : (
                      <Button
                        className="entry-catalog-action"
                        onClick={() => setRequestItemEntryId(entry.id)}
                        variant="ghost"
                      >
                        Can't find it? Request from admin
                      </Button>
                    )}
                  </div>
                  <Field
                    error={entryErrors.size}
                    label="Specifications/Size"
                    required={Boolean(selectedItem?.specifications.length)}
                  >
                    <Select
                      disabled={!selectedItem}
                      value={entry.size}
                      onChange={(event) => {
                        const nextSize = event.target.value;
                        const nextPackSize =
                          selectedItem?.specificationPackSizes?.find(
                            (specification) =>
                              specification.label === nextSize,
                          )?.packSize;
                        updateEntry(entry.id, "size", nextSize);
                        if (entry.enteredUnit === "BALE") {
                          updateEntry(
                            entry.id,
                            "piecesPerBale",
                            nextPackSize != null ? String(nextPackSize) : "",
                          );
                        }
                      }}
                    >
                      <option value="">Select specifications/size</option>
                      {(selectedItem?.specifications ?? []).map(
                        (specification) => (
                          <option key={specification} value={specification}>
                            {specification}
                          </option>
                        ),
                      )}
                    </Select>
                  </Field>
                  <div className="entry-quantity-section">
                    <Field label="Quantity unit">
                      <Select
                        disabled={!selectedItem}
                        value={entry.enteredUnit}
                        onChange={(event) => {
                          const enteredUnit = event.target.value;
                          updateEntry(entry.id, "enteredUnit", enteredUnit);
                          updateEntry(
                            entry.id,
                            "piecesPerBale",
                            enteredUnit === "BALE" && packSize != null
                              ? String(packSize)
                              : "",
                          );
                        }}
                      >
                        {selectedItem?.unit === "KG" ? (
                          <option value="KG">kg</option>
                        ) : (
                          <>
                            <option value="PCS">pcs</option>
                            <option value="BALE">bales</option>
                          </>
                        )}
                      </Select>
                    </Field>
                    <div className="entry-quantity-fields">
                      <Field
                        error={entryErrors.quantityIn || entryErrors.quantity}
                        label={`Quantity In (${enteredUnitLabel})`}
                      >
                        <Input
                          min="0"
                          step={quantityStep}
                          type="number"
                          value={entry.quantityIn ?? ""}
                          onChange={(event) =>
                            updateEntry(
                              entry.id,
                              "quantityIn",
                              event.target.value,
                            )
                          }
                        />
                      </Field>
                      <Field
                        error={
                          entryErrors.quantityOut || entryErrors.quantity
                        }
                        label={`Quantity Out (${enteredUnitLabel})`}
                      >
                        <Input
                          min="0"
                          step={quantityStep}
                          type="number"
                          value={entry.quantityOut ?? ""}
                          onChange={(event) =>
                            updateEntry(
                              entry.id,
                              "quantityOut",
                              event.target.value,
                            )
                          }
                        />
                      </Field>
                    </div>
                    {isBaleUnit && (
                      <section className="entry-bale-contents" aria-label="Bale contents">
                        <h3>Bale contents</h3>
                        {packSize != null && (
                          <small>Standard pack: {packSize} pcs</small>
                        )}
                        <div className="entry-quantity-fields">
                          <Field
                            error={entryErrors.piecesPerBale}
                            label="Pieces per bale"
                            required
                          >
                            <Input
                              min="1"
                              max="10000"
                              step="1"
                              type="number"
                              value={entry.piecesPerBale}
                              onChange={(event) =>
                                updateEntry(
                                  entry.id,
                                  "piecesPerBale",
                                  event.target.value,
                                )
                              }
                            />
                          </Field>
                          <div className="entry-bale-totals" aria-live="polite">
                            <div>
                              <span>Total pieces in</span>
                              <strong>
                                {totalPiecesIn == null
                                  ? "–"
                                  : `${totalPiecesIn.toLocaleString("en-US")} pcs`}
                              </strong>
                            </div>
                            <div>
                              <span>Total pieces out</span>
                              <strong>
                                {totalPiecesOut == null
                                  ? "–"
                                  : `${totalPiecesOut.toLocaleString("en-US")} pcs`}
                              </strong>
                            </div>
                          </div>
                        </div>
                      </section>
                    )}
                  </div>
                  <Field
                    className="entry-handler-field"
                    error={entryErrors.handledBy}
                    hint="Enter the full name of the person receiving stock into or dispatching it from the godown."
                    label="Person who received / dispatched the stock"
                    required
                  >
                    <Input
                      autoComplete="name"
                      maxLength={160}
                      onChange={(event) =>
                        updateEntry(entry.id, "handledBy", event.target.value)
                      }
                      placeholder="Full name of recipient / dispatcher"
                      required
                      value={entry.handledBy}
                    />
                  </Field>
                  <Field className="entry-description" label="Description">
                    <textarea
                      className="input textarea"
                      onChange={(event) =>
                        updateEntry(entry.id, "details", event.target.value)
                      }
                      placeholder="Add a description"
                      rows="4"
                      value={entry.details}
                    />
                  </Field>
                </div>
              </section>
            );
          })}
        </div>
        {pageError && (
          <p className="entry-form-error" role="alert">
            {pageError.message}
          </p>
        )}
        <Button
          className="entry-add-row"
          onClick={addEntry}
          variant="secondary"
        >
          <Plus aria-hidden="true" size={16} />
          Add another entry
        </Button>
        <div className="entry-form-actions">
          <Button onClick={() => navigate("/inventory")} variant="secondary">
            Cancel
          </Button>
          <Button loading={submitting} type="submit">
            Review {entries.length === 1 ? "entry" : `${entries.length} entries`}
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
          <Button
            onClick={() => setRequestItemEntryId(entries[0].id)}
            variant="secondary"
          >
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
          initialCategoryId={
            categories.find(
              (category) =>
                category.name === activeAddItemEntry?.category,
            )?.id ?? ""
          }
          onClose={() => setAddItemEntryId(null)}
          onCreated={handleItemCreated}
          open={Boolean(activeAddItemEntry)}
        />
      ) : (
        <RequestItemModal
          categories={categories}
          items={catalogItems}
          initialCategoryId={
            categories.find(
              (category) =>
                category.name === activeRequestItemEntry?.category,
            )?.id ?? ""
          }
          initialItemName={activeRequestItemEntry?.item ?? ""}
          onClose={() => setRequestItemEntryId(null)}
          onCreated={handleRequestCreated}
          open={Boolean(activeRequestItemEntry)}
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