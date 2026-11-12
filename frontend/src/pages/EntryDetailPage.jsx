import { ArrowLeft, Pencil, Save, X } from "lucide-react"
import { useEffect, useState } from "react"
import {
  Link,
  useLocation,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router"
import {
  Button,
  ErrorState,
  Field,
  Input,
  LoadingState,
  PageHeader,
  Select,
  StatusBadge,
} from "../components/ui"
import { useAuth } from "../context/AuthContext"
import { useApi } from "../hooks/useApi"
import { api } from "../services/api"
import { formatDate, formatDateTime } from "../utils/format"

function recordForm(record) {
  return {
    date: record.date,
    category: record.category,
    item: record.item,
    size: record.size,
    quantityIn: record.quantityIn ?? "",
    quantityOut: record.quantityOut ?? "",
    handledBy: record.handledBy ?? "",
    details: record.details ?? "",
    status: record.status,
    enteredUnit: record.enteredUnit,
  }
}

function StockFigure({ stock, loading, error, onRetry, context = false }) {
  if (loading) {
    return (
      <span aria-label="Loading stock" className="entry-stock-skeleton" role="status">
        <span aria-hidden="true" className="skeleton" />
      </span>
    )
  }

  if (error || !stock) {
    return (
      <span aria-live="polite" className="entry-stock-error" role="status">
        <span>Stock unavailable</span>
        <button
          className="entry-stock-retry"
          onClick={onRetry}
          type="button"
        >
          Retry
        </button>
      </span>
    )
  }

  const isNegative = stock.quantity < 0
  const isZero = stock.quantity === 0
  const state = isNegative ? "negative" : isZero ? "zero" : "positive"

  return (
    <span
      aria-atomic="true"
      aria-live="polite"
      className={`entry-stock-value entry-stock-value-${state}`}
    >
      <strong>{stock.display}</strong>
      {isNegative && (
        <small>Stock is below zero. Check recent entries.</small>
      )}
      {isZero && <small>Out of stock</small>}
      {context && (
        <>
          <small>
            In minus Out across all entries for {stock.itemName}
            {stock.sizeLabel ? ` . ${stock.sizeLabel}` : ""} at{" "}
            {stock.locationName}
          </small>
          <small>
            As of {formatDateTime(stock.asOf).replace(" at ", " ")}
          </small>
        </>
      )}
    </span>
  )
}

export default function EntryDetailPage() {
  const { id } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const { isAdmin } = useAuth()
  const {
    data: record,
    setData: setRecord,
    error,
    loading,
    reload,
  } = useApi(() => api.getInventoryById(id), [id])
  const {
    data: stock,
    error: stockError,
    loading: stockLoading,
    reload: reloadStock,
  } = useApi(() => api.getInventoryStock(id), [id])
  const {
    data: catalog,
    error: catalogError,
    loading: catalogLoading,
  } = useApi(() => api.getCatalog(), [])
  const editRequested =
    isAdmin &&
    (searchParams.get("edit") === "true" || location.pathname.endsWith("/edit"))
  const [editing, setEditing] = useState(editRequested)
  const [form, setForm] = useState(null)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState("")

  useEffect(() => {
    if (!record) return
    setForm(recordForm(record))
    setEditing(editRequested)
  }, [record, editRequested])

  useEffect(() => {
    function refreshStock() {
      if (document.visibilityState === "visible") {
        void reloadStock()
      }
    }

    window.addEventListener("focus", refreshStock)
    window.addEventListener("inventory-stock-changed", refreshStock)
    document.addEventListener("visibilitychange", refreshStock)
    return () => {
      window.removeEventListener("focus", refreshStock)
      window.removeEventListener("inventory-stock-changed", refreshStock)
      document.removeEventListener("visibilitychange", refreshStock)
    }
  }, [reloadStock])

  if (loading || catalogLoading) {
    return (
      <>
        <PageHeader title="Inventory record" />
        <section className="panel">
          <LoadingState label="Loading inventory record" rows={3} />
        </section>
      </>
    )
  }
  if (error || catalogError) {
    const requestError = error ?? catalogError
    return (
      <ErrorState
        message={requestError.message}
        onRetry={() => {
          void reload()
        }}
        retrying={loading}
        title="Unable to load inventory record"
      />
    )
  }
  if (!record || !form) return null

  const categories = catalog?.categories ?? []
  const items = catalog?.items ?? []
  const category = categories.find((entry) => entry.name === form.category)
  const categoryItems = items.filter((item) => item.categoryId === category?.id)
  const item = categoryItems.find((entry) => entry.name === form.item)
  const specifications = item?.specifications ?? []
  const isOriginalItem =
    form.category === record.category && form.item === record.item
  const selectedSizeIsAvailable = specifications.includes(form.size)

  function update(key, value) {
    const selectedItem =
      key === "item"
        ? categoryItems.find((entry) => entry.name === value)
        : null
    setForm((current) => ({
      ...current,
      [key]: value,
      ...(key === "category"
        ? { item: "", size: "", enteredUnit: "PCS" }
        : {}),
      ...(key === "item"
        ? {
            size: "",
            enteredUnit: selectedItem?.inventoryUnit ?? "PCS",
          }
        : {}),
    }))
    setSaveError("")
  }

  async function save(event) {
    event.preventDefault()
    setSaving(true)
    setSaveError("")
    try {
      const response = await api.updateInventory(id, form)
      setRecord(response.data)
      await reloadStock()
      setEditing(false)
      if (location.pathname.endsWith("/edit")) {
        navigate(`/inventory/${encodeURIComponent(id)}`, { replace: true })
        return
      }
      const nextParams = new URLSearchParams(searchParams)
      nextParams.delete("edit")
      setSearchParams(nextParams, { replace: true })
    } catch (requestError) {
      setSaveError(requestError.message)
    } finally {
      setSaving(false)
    }
  }

  function cancelEdit() {
    setForm(recordForm(record))
    setEditing(false)
    setSaveError("")
    if (location.pathname.endsWith("/edit")) {
      navigate(`/inventory/${encodeURIComponent(id)}`, { replace: true })
      return
    }
    if (searchParams.has("edit")) {
      const nextParams = new URLSearchParams(searchParams)
      nextParams.delete("edit")
      setSearchParams(nextParams, { replace: true })
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
                {!categories.some(
                  (entry) => entry.name === record.category,
                ) && <option value={record.category}>{record.category}</option>}
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
                {form.category === record.category &&
                  !categoryItems.some(
                    (entry) => entry.name === record.item,
                  ) && <option value={record.item}>{record.item}</option>}
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
                required={Boolean(specifications.length || isOriginalItem)}
                value={form.size}
              >
                <option value="">Select specifications/size</option>
                {isOriginalItem && !selectedSizeIsAvailable && (
                  <option value={record.size}>{record.size}</option>
                )}
                {specifications.map((specification) => (
                  <option key={specification} value={specification}>
                    {specification}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label={`Quantity In (${form.enteredUnit})`}>
              <Input
                min="0"
                onChange={(event) => update("quantityIn", event.target.value)}
                step={form.enteredUnit === "BALE" ? "1" : "0.001"}
                type="number"
                value={form.quantityIn}
              />
            </Field>
            <Field label={`Quantity Out (${form.enteredUnit})`}>
              <Input
                min="0"
                onChange={(event) => update("quantityOut", event.target.value)}
                step={form.enteredUnit === "BALE" ? "1" : "0.001"}
                type="number"
                value={form.quantityOut}
              />
            </Field>
            <Field label="Received / dispatched by" required>
              <Input
                autoComplete="name"
                maxLength={160}
                onChange={(event) => update("handledBy", event.target.value)}
                required
                value={form.handledBy}
              />
            </Field>
            <Field label="Entered unit">
              <Select
                disabled
                value={form.enteredUnit}
              >
                <option value={form.enteredUnit}>{form.enteredUnit}</option>
              </Select>
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
          {saveError && (
            <p className="entry-form-error" role="alert">
              {saveError}
            </p>
          )}
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
        <section aria-label="Inventory record details" className="panel entry-record-card">
          <header className="entry-record-hero">
            <div className="entry-record-hero-meta">
              <span className="entry-record-category">{record.category}</span>
              <StatusBadge status={record.status} />
            </div>
            <div className="entry-record-title-row">
              <h2>{record.item}</h2>
              <div
                aria-label={
                  stockLoading
                    ? "In stock: loading"
                    : stockError || !stock
                      ? "In stock: stock unavailable"
                      : `In stock: ${stock.display}`
                }
                className="entry-record-stock-stat"
              >
                <span className="entry-record-stock-stat-label">In stock</span>
                <StockFigure
                  error={stockError}
                  loading={stockLoading}
                  onRetry={() => {
                    void reloadStock()
                  }}
                  stock={stock}
                />
              </div>
            </div>
            <p>{record.size || "No specification or size recorded"}</p>
          </header>
          <dl aria-label="Quantity movement" className="entry-record-quantities">
            <div className="entry-record-quantity-in">
              <dt>Quantity In</dt>
              <dd>
                <span>{record.quantityIn ?? "–"}</span>
                <small>{record.enteredUnit}</small>
              </dd>
            </div>
            <div className="entry-record-quantity-out">
              <dt>Quantity Out</dt>
              <dd>
                <span>{record.quantityOut ?? "–"}</span>
                <small>{record.enteredUnit}</small>
              </dd>
            </div>
          </dl>
          <dl className="entry-record-fields">
            <div>
              <dt>Date</dt>
              <dd>{formatDate(record.date)}</dd>
            </div>
            <div>
              <dt>Entered unit</dt>
              <dd>{record.enteredUnit}</dd>
            </div>
            <div>
              <dt>Added by</dt>
              <dd>{record.addedBy}</dd>
            </div>
            <div>
              <dt>Received / dispatched by</dt>
              <dd>{record.handledBy || "–"}</dd>
            </div>
            <div>
              <dt>Last modified by</dt>
              <dd>{record.modifiedBy}</dd>
            </div>
            <div className="entry-record-stock-card">
              <dt>Stock remaining</dt>
              <dd>
                <StockFigure
                  context
                  error={stockError}
                  loading={stockLoading}
                  onRetry={() => {
                    void reloadStock()
                  }}
                  stock={stock}
                />
              </dd>
            </div>
            <div className="entry-record-details">
              <dt>Details</dt>
              <dd>{record.details || "–"}</dd>
            </div>
          </dl>
        </section>
      )}
      <Link className="entry-back-link" to="/inventory">
        <ArrowLeft aria-hidden="true" size={16} />
        Back to inventory
      </Link>
    </section>
  )
}
