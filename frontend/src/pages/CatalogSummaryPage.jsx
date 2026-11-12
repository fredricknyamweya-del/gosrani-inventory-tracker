import { Search } from "lucide-react";
import { useMemo, useState } from "react";
import {
  EmptyState,
  ErrorState,
  Input,
  LoadingState,
  PageHeader,
  Select,
} from "../components/ui";
import { useApi } from "../hooks/useApi";
import { api } from "../services/api";
import { formatDate } from "../utils/format";

function unitName(unit) {
  if (unit === "BALE") return "Bales";
  if (unit === "KG") return "Kg";
  return "Pieces";
}

function formatQuantity(quantity) {
  return Number(quantity ?? 0).toLocaleString(undefined, {
    maximumFractionDigits: 3,
  });
}

export default function CatalogSummaryPage() {
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [unit, setUnit] = useState("");
  const [sort, setSort] = useState("name");
  const { data, error, loading, reload } = useApi(
    () => api.getCatalogSummary(),
    [],
  );
  const products = data?.products ?? [];
  const categories = useMemo(
    () => [...new Set(products.map((product) => product.category))].sort(
      (left, right) => left.localeCompare(right),
    ),
    [products],
  );
  const visibleProducts = useMemo(() => {
    const query = search.trim().toLocaleLowerCase();
    return products
      .filter((product) => {
        const matchesSearch = !query ||
          product.productName.toLocaleLowerCase().includes(query);
        const matchesCategory = !category || product.category === category;
        const matchesUnit = !unit || product.inventoryUnit === unit;
        return matchesSearch && matchesCategory && matchesUnit;
      })
      .sort((left, right) => {
        if (sort === "category") {
          return left.category.localeCompare(right.category) ||
            left.productName.localeCompare(right.productName);
        }
        if (sort === "remaining") {
          return right.remainingStock - left.remainingStock ||
            left.productName.localeCompare(right.productName);
        }
        return left.productName.localeCompare(right.productName);
      });
  }, [products, search, category, unit, sort]);
  const totals = data?.totals ?? {};

  return (
    <section className="catalog-summary-page">
      <PageHeader
        description="Review every registered product and its stock position in your assigned locations."
        eyebrow="Inventory overview"
        title="Catalogue summary"
      />

      {error ? (
        <ErrorState
          message={error.message}
          onRetry={reload}
          retrying={loading}
          title="Unable to load catalogue summary"
        />
      ) : (
        <>
          <section aria-label="Catalogue totals" className="catalog-summary-stats">
            <article className="panel catalog-summary-stat">
              <span>Registered products</span>
              <strong>{totals.registeredProducts ?? 0}</strong>
            </article>
            <article className="panel catalog-summary-stat">
              <span>Bale-based products</span>
              <strong>{totals.baleBasedProducts ?? 0}</strong>
            </article>
            <article className="panel catalog-summary-stat">
              <span>Piece-based products</span>
              <strong>{totals.pieceBasedProducts ?? 0}</strong>
            </article>
            <article className="panel catalog-summary-stat">
              <span>Stock entries recorded</span>
              <strong>{totals.stockEntries ?? 0}</strong>
            </article>
          </section>

          <section aria-label="Catalogue summary filters" className="panel catalog-summary-filters">
            <label className="catalog-summary-search">
              <Search aria-hidden="true" size={17} />
              <span className="sr-only">Search products</span>
              <Input
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search product name"
                type="search"
                value={search}
              />
            </label>
            <label className="catalog-summary-filter">
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
            <label className="catalog-summary-filter">
              <span>Inventory unit</span>
              <Select
                onChange={(event) => setUnit(event.target.value)}
                value={unit}
              >
                <option value="">All units</option>
                <option value="PCS">Pieces</option>
                <option value="BALE">Bales</option>
                <option value="KG">Kilograms</option>
              </Select>
            </label>
            <label className="catalog-summary-filter">
              <span>Sort by</span>
              <Select
                onChange={(event) => setSort(event.target.value)}
                value={sort}
              >
                <option value="name">Product name</option>
                <option value="category">Category</option>
                <option value="remaining">Remaining stock</option>
              </Select>
            </label>
          </section>

          <section aria-label="Product summaries" className="panel catalog-summary-table-panel">
            {loading ? (
              <LoadingState label="Loading product summaries" rows={6} />
            ) : visibleProducts.length ? (
              <div className="table-scroll">
                <table className="data-table catalog-summary-table">
                  <thead>
                    <tr>
                      <th scope="col">No.</th>
                      <th scope="col">Product Name</th>
                      <th scope="col">Category</th>
                      <th scope="col">Inventory Unit</th>
                      <th scope="col">Pieces per Bale</th>
                      <th scope="col">Total Stock In</th>
                      <th scope="col">Total Stock Out</th>
                      <th scope="col">Remaining Stock</th>
                      <th scope="col">Equivalent Pieces</th>
                      <th scope="col">Total Entries</th>
                      <th scope="col">Last Transaction</th>
                    </tr>
                  </thead>
                  <tbody>
                    {visibleProducts.map((product, index) => (
                      <tr key={product.id}>
                        <td>{index + 1}</td>
                        <td className="catalog-summary-product">{product.productName}</td>
                        <td>{product.category}</td>
                        <td>{unitName(product.inventoryUnit)}</td>
                        <td>{product.piecesPerBale ?? "–"}</td>
                        <td>{formatQuantity(product.totalStockIn)} {unitName(product.inventoryUnit)}</td>
                        <td>{formatQuantity(product.totalStockOut)} {unitName(product.inventoryUnit)}</td>
                        <td>{formatQuantity(product.remainingStock)} {unitName(product.inventoryUnit)}</td>
                        <td>
                          {product.equivalentPieces == null
                            ? "–"
                            : `${formatQuantity(product.equivalentPieces)} Pieces`}
                        </td>
                        <td>{product.totalEntries}</td>
                        <td>{product.lastTransactionDate ? formatDate(product.lastTransactionDate) : "–"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState
                description={
                  products.length
                    ? "Try changing the search text or filters."
                    : "Registered products will appear here."
                }
                title={
                  products.length
                    ? "No products match these filters"
                    : "No products in the catalogue"
                }
              />
            )}
          </section>
        </>
      )}
    </section>
  );
}
