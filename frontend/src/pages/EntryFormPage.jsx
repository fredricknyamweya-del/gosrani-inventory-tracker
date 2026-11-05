import { useState } from "react";
import { ArrowLeft, Check, Save } from "lucide-react";
import { Link, useNavigate } from "react-router";
import {
  Button,
  ErrorState,
  Field,
  Input,
  LoadingState,
  PageHeader,
  Select,
} from "../components/ui";
import { useApi } from "../hooks/useApi";
import { api } from "../services/api";
import { todayIso } from "../utils/format";

function makeEntry() {
  return {
    date: todayIso(),
    category: "",
    item: "",
    size: "",
    quantityIn: "",
    quantityOut: "",
    details: "",
  };
}

function validateEntry(entry, item) {
  const errors = {};

  if (!entry.date) errors.date = "Entry date is required.";
  if (!entry.category) errors.category = "Category is required.";
  if (!entry.item) errors.item = "Name of Item is required.";
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
  const navigate = useNavigate();
  const [entry, setEntry] = useState(makeEntry);
  const [errors, setErrors] = useState({});
  const [stage, setStage] = useState("form");
  const [verified, setVerified] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [pageError, setPageError] = useState(null);
  const [savedEntry, setSavedEntry] = useState(null);
  const {
    data: catalog,
    error: catalogError,
    loading: catalogLoading,
    reload: reloadCatalog,
  } = useApi(() => api.getCatalog(), []);

  const categories = catalog?.categories ?? [];
  const selectedCategory = categories.find(
    (category) => category.name === entry.category,
  );
  const availableItems = (catalog?.items ?? []).filter(
    (item) => item.active && item.categoryId === selectedCategory?.id,
  );
  const selectedItem = availableItems.find((item) => item.name === entry.item);

  function update(key, value) {
    setEntry((current) => ({ ...current, [key]: value }));
    setErrors((current) => ({ ...current, [key]: "", quantity: "" }));
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
      <>
        <PageHeader
          description="Confirm the entry details before saving."
          eyebrow="Final check"
          title="Review your entry"
        />
        <section className="panel entry-form-panel">
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
      </>
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
    </>
  );
}