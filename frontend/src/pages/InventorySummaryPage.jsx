import { Download, Search } from "lucide-react";
import { useMemo, useState } from "react";
import {
  Button,
  EmptyState,
  ErrorState,
  Input,
  LoadingState,
  PageHeader,
  Select,
} from "../components/ui";
import QuantityDisplay from "../components/QuantityDisplay";
import { useApi } from "../hooks/useApi";
import { api } from "../services/api";

function csvCell(value) {
  const text = String(value ?? "");
  const safeText = /^[\u0000-\u0020]*[=+\-@]/.test(text)
    ? `'${text}`
    : text;
  return `"${safeText.replace(/"/g, '""')}"`;
}

export default function InventorySummaryPage() {
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [size, setSize] = useState("");
  const [unit, setUnit] = useState("");
  const { data, error, loading, reload } = useApi(
    () => api.getInventorySummary(),
    [],
  );
  const stockRows = data?.stockBySpecification ?? [];
  const categories = useMemo(
    () => [...new Set(stockRows.map((row) => row.category))].sort(
      (left, right) => left.localeCompare(right),
    ),
    [stockRows],
  );
  const sizes = useMemo(
    () => [...new Set(stockRows.map((row) => row.size))].sort(
      (left, right) => left.localeCompare(right),
    ),
    [stockRows],
  );
  const units = useMemo(
    () => [...new Set(stockRows.map((row) => row.entryUnit))].sort(
      (left, right) => left.localeCompare(right),
    ),
    [stockRows],
  );
  const visibleRows = useMemo(() => {
    const query = search.trim().toLocaleLowerCase();
    return stockRows.filter((row) => {
      const matchesSearch = !query ||
        `${row.itemName} ${row.size}`.toLocaleLowerCase().includes(query);
      return matchesSearch &&
        (!category || row.category === category) &&
        (!size || row.size === size) &&
        (!unit || row.entryUnit === unit);
    });
  }, [stockRows, search, category, size, unit]);

  function exportCsv() {
    const rows = [
      ["Item Name", "Category", "Size", "Total Stock Left"],
      ...visibleRows.map((row) => [
        row.itemName,
        row.category,
        row.size,
        [row.display, row.secondaryDisplay].filter(Boolean).join(" "),
      ]),
    ];
    const csvRows = rows.map((row) => row.map(csvCell).join(","));
    const csv = `\uFEFF${csvRows.join("\r\n")}`;
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download =
      `inventory-summary-${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.append(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 0);
  }

  return (
    <section className="inventory-summary-page">
      <PageHeader
        className="inventory-summary-header"
        description="A clear, size-by-size view of the stock remaining across your assigned locations."
        eyebrow="Stock at a glance"
        actions={
          <Button
            disabled={loading || Boolean(error) || visibleRows.length === 0}
            onClick={exportCsv}
            variant="secondary"
          >
            <Download aria-hidden="true" size={16} />
            Export CSV
          </Button>
        }
        title="Inventory summary"
      />

      {error ? (
        <ErrorState
          message={error.message}
          onRetry={reload}
          retrying={loading}
          title="Unable to load inventory summary"
        />
      ) : (
        <>
          <section aria-label="Inventory summary filters" className="panel inventory-summary-filters">
            <label className="inventory-summary-search">
              <Search aria-hidden="true" size={18} />
              <span className="sr-only">Search item name or size</span>
              <Input
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search item name or size"
                type="search"
                value={search}
              />
            </label>
            <label className="inventory-summary-filter">
              <span>Category</span>
              <Select
                onChange={(event) => setCategory(event.target.value)}
                value={category}
              >
                <option value="">All categories</option>
                {categories.map((entry) => (
                  <option key={entry} value={entry}>{entry}</option>
                ))}
              </Select>
            </label>
            <label className="inventory-summary-filter">
              <span>Size</span>
              <Select
                onChange={(event) => setSize(event.target.value)}
                value={size}
              >
                <option value="">All sizes</option>
                {sizes.map((entry) => (
                  <option key={entry} value={entry}>{entry}</option>
                ))}
              </Select>
            </label>
            <label className="inventory-summary-filter">
              <span>Unit</span>
              <Select
                onChange={(event) => setUnit(event.target.value)}
                value={unit}
              >
                <option value="">All units</option>
                {units.map((entry) => (
                  <option key={entry} value={entry}>
                    {entry === "PCS"
                      ? "Pieces"
                      : entry === "BALE"
                        ? "Bales"
                        : "Kilograms"}
                  </option>
                ))}
              </Select>
            </label>
          </section>

          <section aria-label="Stock by item and size" className="panel inventory-summary-table-panel">
            {loading ? (
              <LoadingState label="Loading inventory summary" rows={6} />
            ) : visibleRows.length ? (
              <div className="table-scroll">
                <table className="data-table inventory-summary-table">
                  <thead>
                    <tr>
                      <th scope="col">Item Name</th>
                      <th scope="col">Category</th>
                      <th scope="col">Size</th>
                      <th scope="col">Total Stock Left</th>
                    </tr>
                  </thead>
                  <tbody>
                    {visibleRows.map((row) => (
                      <tr key={row.id}>
                        <td className="inventory-summary-item">{row.itemName}</td>
                        <td>{row.category}</td>
                        <td>
                          <span className="inventory-summary-size">{row.size}</span>
                        </td>
                        <td>
                          <QuantityDisplay
                            display={row.display}
                            secondary={row.secondaryDisplay}
                          />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState
                description={
                  stockRows.length
                    ? "Try another search or clear the selected filters."
                    : "Item sizes and their current stock will appear here."
                }
                title={
                  stockRows.length
                    ? "No stock matches these filters"
                    : "No inventory to summarize"
                }
              />
            )}
          </section>
        </>
      )}
    </section>
  );
}
