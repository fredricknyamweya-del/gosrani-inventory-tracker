import { useEffect, useState } from "react";
import { api } from "../services/api";
import { Button, Field, Input, Modal, Select } from "./ui";

export default function RequestItemModal({
  open,
  onClose,
  categories,
  items = [],
  initialCategoryId = "",
  initialItemName = "",
  onCreated,
}) {
  const [requestType, setRequestType] = useState("product");
  const [categoryId, setCategoryId] = useState(initialCategoryId);
  const [itemName, setItemName] = useState(initialItemName);
  const [categoryName, setCategoryName] = useState("");
  const [specification, setSpecification] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const availableItems = items.filter(
    (item) => item.categoryId === categoryId && item.active,
  );

  useEffect(() => {
    if (!open) return;
    setRequestType("product");
    setCategoryId(initialCategoryId);
    setItemName(initialItemName);
    setCategoryName("");
    setSpecification("");
    setNote("");
    setError("");
  }, [open, initialCategoryId, initialItemName]);

  function updateRequestType(value) {
    setRequestType(value);
    setError("");
    setItemName("");
    setSpecification("");
  }

  async function submit(event) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const response = await api.createCatalogRequest({
        requestType,
        ...(requestType === "category"
          ? { categoryName }
          : {
              categoryId,
              ...(requestType === "specification"
                ? { itemId: itemName }
                : { itemName }),
              specification,
            }),
        note,
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
      description="Ask an administrator to add a missing category, product, or specification."
      footer={
        <>
          <Button onClick={onClose} variant="secondary">
            Cancel
          </Button>
          <Button
            form="request-catalog-item-form"
            loading={saving}
            type="submit"
          >
            Send request
          </Button>
        </>
      }
      onClose={onClose}
      open={open}
      title="Request a catalog addition"
    >
      <form
        className="request-item-form"
        id="request-catalog-item-form"
        onSubmit={submit}
      >
        <Field label="What needs to be added?" required>
          <Select
            onChange={(event) => updateRequestType(event.target.value)}
            value={requestType}
          >
            <option value="category">Category</option>
            <option value="product">Product</option>
            <option value="specification">Specification</option>
          </Select>
        </Field>
        {requestType === "category" ? (
          <Field label="Category name" required>
            <Input
              autoComplete="off"
              onChange={(event) => {
                setCategoryName(event.target.value);
                setError("");
              }}
              required
              value={categoryName}
            />
          </Field>
        ) : (
          <>
            <Field label="Category" required>
              <Select
                onChange={(event) => {
                  setCategoryId(event.target.value);
                  setItemName("");
                  setSpecification("");
                  setError("");
                }}
                required
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
            {requestType === "product" ? (
              <Field label="Product name" required>
                <Input
                  autoComplete="off"
                  onChange={(event) => {
                    setItemName(event.target.value);
                    setError("");
                  }}
                  required
                  value={itemName}
                />
              </Field>
            ) : (
              <Field label="Product" required>
                <Select
                  disabled={!categoryId}
                  onChange={(event) => {
                    setItemName(event.target.value);
                    setError("");
                  }}
                  required
                  value={itemName}
                >
                  <option value="">Select product</option>
                  {availableItems.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.name}
                    </option>
                  ))}
                </Select>
              </Field>
            )}
            <Field
              label={
                requestType === "product"
                  ? "Initial specification"
                  : "Missing specification"
              }
              required
            >
              <Input
                autoComplete="off"
                onChange={(event) => {
                  setSpecification(event.target.value);
                  setError("");
                }}
                placeholder="e.g. 2 kg"
                required
                value={specification}
              />
            </Field>
          </>
        )}
        <Field hint="Optional" label="Note">
          <textarea
            className="input textarea"
            onChange={(event) => setNote(event.target.value)}
            rows={3}
            value={note}
          />
        </Field>
        {error && (
          <p className="entry-form-error" role="alert">
            {error}
          </p>
        )}
      </form>
    </Modal>
  );
}
