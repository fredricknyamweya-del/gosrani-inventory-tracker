import { Plus, X } from "lucide-react";
import { useEffect, useState } from "react";
import {
  findCatalogNearMatch,
  getCatalogSpecificationExample,
  api,
} from "../services/api";
import { Button, Field, Input, Modal, Select } from "./ui";

function normalize(value) {
  return String(value ?? "").trim().replace(/\s+/g, " ").toLocaleLowerCase();
}

export default function AddItemModal({
  open,
  onClose,
  categories,
  items = [],
  initialCategoryId = "",
  onCreated,
}) {
  const [categoryId, setCategoryId] = useState(initialCategoryId);
  const [name, setName] = useState("");
  const [specifications, setSpecifications] = useState([""]);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    setCategoryId(initialCategoryId);
    setName("");
    setSpecifications([""]);
    setError("");
  }, [open, initialCategoryId]);

  const nearMatch = categoryId && name.trim()
    ? findCatalogNearMatch(name, categoryId)
    : null;
  const exactMatch = nearMatch && normalize(nearMatch) === normalize(name);
  const specificationExample = getCatalogSpecificationExample(
    items,
    categoryId,
  );

  function updateSpecification(index, value) {
    setSpecifications((current) =>
      current.map((specification, currentIndex) =>
        currentIndex === index ? value : specification,
      ),
    );
    setError("");
  }

  async function submit(event) {
    event.preventDefault();
    const cleanSpecifications = specifications
      .map((specification) => specification.trim())
      .filter(Boolean);

    if (!categoryId) {
      setError("Choose a category.");
      return;
    }
    if (!name.trim()) {
      setError("Item name is required.");
      return;
    }
    if (exactMatch) {
      setError(`An item named "${nearMatch}" already exists in this category.`);
      return;
    }
    if (cleanSpecifications.length === 0) {
      setError("Add at least one specification.");
      return;
    }

    setSaving(true);
    setError("");
    try {
      const response = await api.createCatalogItem({
        categoryId,
        name,
        specifications: cleanSpecifications,
      });
      await onCreated?.(response.data);
      onClose();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal
      description="Choose a category, name the item, and add at least one specification."
      footer={
        <>
          <Button onClick={onClose} variant="secondary">
            Cancel
          </Button>
          <Button
            disabled={Boolean(exactMatch)}
            form="add-catalog-item-form"
            loading={saving}
            type="submit"
          >
            Add item
          </Button>
        </>
      }
      onClose={onClose}
      open={open}
      title="Add catalog item"
    >
      <form
        className="catalog-dialog-form"
        id="add-catalog-item-form"
        onSubmit={submit}
      >
        <Field label="Category" required>
          <Select
            onChange={(event) => {
              setCategoryId(event.target.value);
              setError("");
            }}
            value={categoryId}
          >
            <option value="">Select category</option>
            {categories.map((category) => (
              <option key={category.id} value={category.id}>
                {category.name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Item name" required>
          <Input
            autoComplete="off"
            onChange={(event) => {
              setName(event.target.value);
              setError("");
            }}
            value={name}
          />
        </Field>
        {exactMatch ? (
          <p className="catalog-inline-error" role="alert">
            An item named “{nearMatch}” already exists in this category.
          </p>
        ) : (
          nearMatch && (
            <p className="catalog-hint">Did you mean {nearMatch}?</p>
          )
        )}
        <div className="catalog-specification-fields">
          <div className="catalog-specification-heading">
            <strong>Specifications</strong>
            <Button
              onClick={() => setSpecifications((current) => [...current, ""])}
              variant="secondary"
            >
              <Plus aria-hidden="true" size={16} />
              Add specification
            </Button>
          </div>
          {specifications.map((specification, index) => (
            <div className="catalog-specification-input" key={index}>
              <Input
                aria-label={`Specification ${index + 1}`}
                autoComplete="off"
                onChange={(event) =>
                  updateSpecification(index, event.target.value)
                }
                placeholder={
                  specificationExample
                    ? `e.g. ${specificationExample}`
                    : "e.g. Standard"
                }
                value={specification}
              />
              {specifications.length > 1 && (
                <button
                  aria-label={`Remove specification ${index + 1}`}
                  className="icon-btn"
                  onClick={() =>
                    setSpecifications((current) =>
                      current.filter((_, currentIndex) => currentIndex !== index),
                    )
                  }
                  type="button"
                >
                  <X aria-hidden="true" size={17} />
                </button>
              )}
            </div>
          ))}
        </div>
        {error && (
          <p className="catalog-inline-error" role="alert">
            {error}
          </p>
        )}
      </form>
    </Modal>
  );
}
