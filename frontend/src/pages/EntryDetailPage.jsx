import { ArrowLeft, Pencil, Save, X } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useLocation, useParams, useSearchParams } from "react-router";
import {
  Button,
  ErrorState,
  Field,
  Input,
  LoadingState,
  PageHeader,
  Select,
} from "../components/ui";
import { useAuth } from "../context/AuthContext";
import { useApi } from "../hooks/useApi";
import { api } from "../services/api";
import { formatDate } from "../utils/format";

function recordForm(record) {
  return {
    date: record.date,
    category: record.category,
    item: record.item,
    size: record.size,
    quantityIn: record.quantityIn ?? "",
    quantityOut: record.quantityOut ?? "",
    details: record.details ?? "",
    status: record.status,
    enteredUnit: record.enteredUnit,
  };
}

export default function EntryDetailPage() {
  const { id } = useParams();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const { isAdmin } = useAuth();
  const {
    data: record,
    setData: setRecord,
    error,
    loading,
    reload,
  } = useApi(() => api.getInventoryById(id), [id]);
  const {
    data: catalog,
    error: catalogError,
    loading: catalogLoading,
  } = useApi(() => api.getCatalog(), []);
  const editRequested =
    isAdmin &&
    (searchParams.get("edit") === "true" || location.pathname.endsWith("/edit"));
  const [editing, setEditing] = useState(editRequested);
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState("");

  useEffect(() => {
    if (!record) return;
    setForm(recordForm(record));
    setEditing(editRequested);
  }, [record, editRequested]);

  if (loading || catalogLoading) {
    return (
      <>
        <PageHeader title="Inventory record" />
        <section className="panel">
          <LoadingState label="Loading inventory record" rows={3} />
        </section>
      </>
    );
  }
  if (error || catalogError) {
    const requestError = error ?? catalogError;
    return (
      <ErrorState
        message={requestError.message}
        onRetry={() => {
          void reload();
        }}
        retrying={loading}
        title="Unable to load inventory record"
      />
    );
  }
  if (!record || !form) return null;

  const categories = catalog?.categories ?? [];
  const items = catalog?.items ?? [];
  const category = categories.find((entry) => entry.name === form.category);
  const categoryItems = items.filter(
    (item) => item.categoryId === category?.id,
  );
  const item = categoryItems.find((entry) => entry.name === form.item);
  const specifications = item?.specifications ?? [];

  function update(key, value) {
    setForm((current) => ({
      ...current,
      [key]: value,
      ...(key === "category" ? { item: "", size: "" } : {}),
      ...(key === "item" ? { size: "" } : {}),
    }));
    setSaveError("");
  }

  async function save(event) {
    event.preventDefault();
    setSaving(true);
    setSaveError("");
    try {
      const response = await api.updateInventory(id, form);
      setRecord(response.data);
      setEditing(false);
      const nextParams = new URLSearchParams(searchParams);
      nextParams.delete("edit");
      setSearchParams(nextParams, { replace: true });
    } catch (requestError) {
      setSaveError(requestError.message);
    } finally {
      setSaving(false);
    }
  }

  function cancelEdit() {
    setForm(recordForm(record));
    setEditing(false);
    setSaveError("");
    if (searchParams.has("edit")) {
      const nextParams = new URLSearchParams(searchParams);
      nextParams.delete("edit");
      setSearchParams(nextParams, { replace: true });
    }
  }

  return (
    <section className="entry-detail-page">
      <PageHeader
        actions={
          isAdmin && !editing ? (
            <Button onClick={() => setEditing(true)}>
              <Pencil aria-hidden="true" size={16} />
              Edit record
            </Button>
          ) : null
        }
        description={`Record #${record.id} · Added by ${record.addedBy}`}
        eyebrow="Inventory"
        title={editing ? "Edit inventory record" : "Inventory record"}
      />
      {editing ? (
        <form className="panel entry-form-panel" onSubmit={save}>
          <div className="entry-form-grid">
            <Field label="Entry date" required>
              <Input
                onChange={(event) => update("date", event.target.value)}
                required
                type="date"
                value={form.date}
              />
            </Field>
            <Field label="Category" required>
              <Select
                onChange={(event) => update("category", event.target.value)}
                required
                value={form.category}
              >
                {!categories.some((entry) => entry.name === record.category) && (
                  <option value={record.category}>{record.category}</option>
                )}
                {categories.map((entry) => (
                  <option key={entry.id} value={entry.name}>
                    {entry.name}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Item" required>
              <Select
                disabled={!category && form.category !== record.category}
                onChange={(event) => update("item", event.target.value)}
                required
                value={form.item}
              >
                {!categoryItems.some((entry) => entry.name === record.item) && (
                  <option value={record.item}>{record.item}</option>
                )}
                {categoryItems.map((entry) => (
                  <option key={entry.id} value={entry.name}>
                    {entry.name}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Specification / size" required>
              <Select
                onChange={(event) => update("size", event.target.value)}
                required
                value={form.size}
              >
                {!specifications.includes(record.size) && (
                  <option value={record.size}>{record.size}</option>
                )}
                {specifications.map((specification) => (
                  <option key={specification} value={specification}>
                    {specification}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Quantity In">
              <Input
                min="0"
                onChange={(event) => update("quantityIn", event.target.value)}
                step="0.001"
                type="number"
                value={form.quantityIn}
              />
            </Field>
            <Field label="Quantity Out">
              <Input
                min="0"
                onChange={(event) => update("quantityOut", event.target.value)}
                step="0.001"
                type="number"
                value={form.quantityOut}
              />
            </Field>
            <Field label="Status">
              <Select
                onChange={(event) => update("status", event.target.value)}
                value={form.status}
              >
                <option>Saved</option>
                <option>Locked</option>
              </Select>
            </Field>
            <Field label="Details">
              <Input
                onChange={(event) => update("details", event.target.value)}
                value={form.details}
              />
            </Field>
          </div>
          {saveError && <p className="form-error" role="alert">{saveError}</p>}
          <div className="entry-form-actions">
            <Button disabled={saving} onClick={cancelEdit} variant="secondary">
              <X aria-hidden="true" size={16} />
              Cancel
            </Button>
            <Button loading={saving} type="submit">
              <Save aria-hidden="true" size={16} />
              Save changes
            </Button>
          </div>
        </form>
      ) : (
        <section className="panel entry-review-list">
          <dl>
            <div><dt>Date</dt><dd>{formatDate(record.date)}</dd></div>
            <div><dt>Category</dt><dd>{record.category}</dd></div>
            <div><dt>Item</dt><dd>{record.item}</dd></div>
            <div><dt>Specification / size</dt><dd>{record.size || "–"}</dd></div>
            <div><dt>Quantity In</dt><dd>{record.quantityIn ?? "–"}</dd></div>
            <div><dt>Quantity Out</dt><dd>{record.quantityOut ?? "–"}</dd></div>
            <div><dt>Details</dt><dd>{record.details || "–"}</dd></div>
            <div><dt>Added by</dt><dd>{record.addedBy}</dd></div>
            <div><dt>Last modified by</dt><dd>{record.modifiedBy}</dd></div>
            <div><dt>Status</dt><dd>{record.status}</dd></div>
          </dl>
        </section>
      )}
      <Link className="entry-back-link" to="/inventory">
        <ArrowLeft aria-hidden="true" size={16} />
        Back to inventory
      </Link>
    </section>
  );
}