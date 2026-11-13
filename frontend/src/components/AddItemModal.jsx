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
  const [entryUnit, setEntryUnit] = useState("PCS");
  const [specificationPackSizes, setSpecificationPackSizes] = useState([""]);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    setCategoryId(initialCategoryId);
    setName("");
    setSpecifications([""]);
    setEntryUnit("PCS");
    setSpecificationPackSizes([""]);
    setError("");
  }, [open, initialCategoryId]);

  const nearMatch = categoryId && name.trim()
    ? findCatalogNearMatch(name, categoryId, items)
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

  function updatePackSize(index, value) {
    setSpecificationPackSizes((current) =>
      current.map((packSize, currentIndex) =>
        currentIndex === index ? value : packSize,
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
    if (
      entryUnit === "BALE" &&
      specificationPackSizes.some((packSize) => {
        if (!packSize) return false;
        const value = Number(packSize);
        return !Number.isInteger(value) || value < 1 || value > 10000;
      })
    ) {
      setError("Standard pieces per bale must be a whole number from 1 to 10000.");
      return;
    }

    setSaving(true);
    setError("");
    try {
      const response = await api.createCatalogItem({
        categoryId,
        name,
        specifications: cleanSpecifications,
        unit: entryUnit === "KG" ? "KG" : "PCS",
        entryUnit,
        specificationPackSizes: cleanSpecifications.map((label) => {
          const index = specifications.findIndex(
            (specification) => specification.trim() === label,
          );
          const rawSize = specificationPackSizes[index];
          return {
            label,
            packSize:
              entryUnit === "BALE" && rawSize !== ""
                ? Number(rawSize)
                : null,
          };
        }),
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
        <Field label="Entered in" required>
          <Select
            onChange={(event) => {
              setEntryUnit(event.target.value);
              setError("");
            }}
            value={entryUnit}
          >
            <option value="PCS">Pieces</option>
            <option value="BALE">Bales</option>
            <option value="KG">Kilograms</option>
          </Select>
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
              onClick={() => {
                setSpecifications((current) => [...current, ""]);
                setSpecificationPackSizes((current) => [...current, ""]);
              }}
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
                  onClick={() => {
                    setSpecifications((current) =>
                      current.filter((_, currentIndex) => currentIndex !== index),
                    );
                    setSpecificationPackSizes((current) =>
                      current.filter((_, currentIndex) => currentIndex !== index),
                    );
                  }}
                  type="button"
                >
                  <X aria-hidden="true" size={17} />
                </button>
              )}
              {entryUnit === "BALE" && (
                <Field
                  label={`Standard pieces per bale for specification ${index + 1}`}
                >
                  <Input
                    max="10000"
                    min="1"
                    onChange={(event) =>
                      updatePackSize(index, event.target.value)
                    }
                    placeholder="Optional"
                    step="1"
                    type="number"
                    value={specificationPackSizes[index] ?? ""}
                  />
                </Field>
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
