import { useState } from "react";
import { KeyRound } from "lucide-react";
import { Button, Field, Input, PageHeader } from "../components/ui";
import { api } from "../services/api";

export default function PasswordChangePage() {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSuccess("");

    if (newPassword.length < 6) {
      setError("New password must contain at least 6 characters.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("New password and confirmation do not match.");
      return;
    }

    setSubmitting(true);
    try {
      await api.changePassword({ currentPassword, newPassword });
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setSuccess(
        "Password changed successfully. Other active sessions have been signed out.",
      );
    } catch (requestError) {
      setError(requestError.message || "Unable to change your password.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section>
      <PageHeader
        eyebrow="ACCOUNT"
        title="Change password"
        description="Use your current password to set a new password for your account."
      />
      <form
        className="panel password-change-panel password-change-form"
        onSubmit={handleSubmit}
      >
        {error && (
          <p className="entry-form-error" role="alert">
            {error}
          </p>
        )}
        {success && (
          <p className="password-change-success" role="status">
            {success}
          </p>
        )}
        <Field label="Current password" required>
          <Input
            autoComplete="current-password"
            onChange={(event) => setCurrentPassword(event.target.value)}
            required
            type="password"
            value={currentPassword}
          />
        </Field>
        <Field
          hint="Use at least 6 characters."
          label="New password"
          required
        >
          <Input
            autoComplete="new-password"
            minLength={6}
            onChange={(event) => setNewPassword(event.target.value)}
            required
            type="password"
            value={newPassword}
          />
        </Field>
        <Field label="Confirm new password" required>
          <Input
            autoComplete="new-password"
            onChange={(event) => setConfirmPassword(event.target.value)}
            required
            type="password"
            value={confirmPassword}
          />
        </Field>
        <div className="password-change-actions">
          <Button loading={submitting} type="submit">
            <KeyRound aria-hidden="true" size={16} />
            Update password
          </Button>
        </div>
      </form>
    </section>
  );
}
