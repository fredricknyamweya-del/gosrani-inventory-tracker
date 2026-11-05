import { useEffect, useState } from "react";
import { api } from "../services/api";
import { Button, Field, Input, Modal, Select } from "./ui";

export default function RequestItemModal({
  open,
  onClose,
  categories,
  initialCategoryId = "",
  initialItemName = "",
  onCreated,
}) {
  const [categoryId, setCategoryId] = useState(initialCategoryId);
  const [itemName, setItemName] = useState(initialItemName);
  const [specification, setSpecification] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    setCategoryId(initialCategoryId);
    setItemName(initialItemName);
    setSpecification("");
    setNote("");
    setError("");
  }, [open, initialCategoryId, initialItemName]);

  async function submit(event) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const response = await api.createCatalogRequest({
        categoryId,
        itemName,
        specification,
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
      description="Tell an administrator which item or specification is missing."
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
      title="Request a catalog item"
    >
      <form
        className="request-item-form"
        id="request-catalog-item-form"
        onSubmit={submit}
      >
        <Field label="Category" required>
          <Select
            onChange={(event) => {
              setCategoryId(event.target.value);
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
        <Field label="Item name" required>
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
        <Field label="Specification" required>
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
