import {
  AlertCircle,
  Check,
  Inbox,
  LoaderCircle,
  X,
} from "lucide-react";
import {
  cloneElement,
  isValidElement,
  useEffect,
  useId,
  useRef,
} from "react";

const buttonVariants = new Set([
  "primary",
  "secondary",
  "ghost",
  "destructive",
]);

export function Button({
  variant = "primary",
  loading = false,
  className = "",
  children,
  disabled = false,
  type = "button",
  ...props
}) {
  const safeVariant = buttonVariants.has(variant) ? variant : "primary";

  return (
    <button
      className={`btn btn-${safeVariant} ${className}`.trim()}
      disabled={loading || disabled}
      type={type}
      {...props}
    >
      {loading ? (
        <LoaderCircle aria-hidden="true" className="spin" size={17} />
      ) : (
        children
      )}
    </button>
  );
}

export function Field({
  label,
  error,
  hint,
  required = false,
  children,
  className = "",
  id,
}) {
  const fieldId = useId();
  const control = isValidElement(children) ? children : null;
  const controlId = id ?? control?.props.id ?? fieldId;
  const hintId = hint ? `${fieldId}-hint` : undefined;
  const errorId = error ? `${fieldId}-error` : undefined;
  const describedBy = [control?.props["aria-describedby"], hintId, errorId]
    .filter(Boolean)
    .join(" ");
  const input = control
    ? cloneElement(control, {
        id: control.props.id ?? controlId,
        "aria-describedby": describedBy || undefined,
        "aria-invalid": error ? true : control.props["aria-invalid"],
      })
    : children;

  return (
    <div className={`field ${className}`.trim()}>
      <label className="field-label" htmlFor={controlId}>
        {label}
        {required && (
          <span aria-hidden="true" className="field-required">
            {" "}
            *
          </span>
        )}
      </label>
      {input}
      {error ? (
        <span className="field-error" id={errorId}>
          <AlertCircle aria-hidden="true" size={14} />
          {error}
        </span>
      ) : hint ? (
        <span className="field-hint" id={hintId}>
          {hint}
        </span>
      ) : null}
    </div>
  );
}

export function Input({ error, className = "", ...props }) {
  return (
    <input
      aria-invalid={Boolean(error) || props["aria-invalid"] || undefined}
      className={`input ${error ? "input-error" : ""} ${className}`.trim()}
      {...props}
    />
  );
}

export function Select({ error, className = "", children, ...props }) {
  return (
    <select
      aria-invalid={Boolean(error) || props["aria-invalid"] || undefined}
      className={`input select ${error ? "input-error" : ""} ${className}`.trim()}
      {...props}
    >
      {children}
    </select>
  );
}

export function StatusBadge({ status }) {
  const normalizedStatus = String(status ?? "").toLowerCase();
  const statusClass =
    normalizedStatus === "saved"
      ? "saved"
      : normalizedStatus === "locked"
        ? "locked"
        : normalizedStatus === "pending"
          ? "warning"
          : "locked";

  return (
    <span className={`status status-${statusClass}`} title={status ?? undefined}>
      {status}
    </span>
  );
}

export function RoleBadge({ role }) {
  const isUser = String(role ?? "").toLowerCase() === "user";
  const label = role ? `${String(role)[0].toUpperCase()}${String(role).slice(1)}` : "";

  return (
    <span className={`role-badge ${isUser ? "role-user" : ""}`.trim()}>
      {label}
    </span>
  );
}

export function PageHeader({ eyebrow, title, description, actions }) {
  return (
    <header className="page-header">
      <div>
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h1>{title}</h1>
        {description && <p>{description}</p>}
      </div>
      {actions && <div className="page-actions">{actions}</div>}
    </header>
  );
}

export function LoadingState({ rows = 5, label = "Loading" }) {
  const rowCount = Math.max(1, Math.min(20, Math.floor(rows)));

  return (
    <div
      aria-label={label}
      aria-live="polite"
      className="skeleton-wrap"
      role="status"
    >
      <span className="sr-only">{label}…</span>
      {Array.from({ length: rowCount }, (_, index) => (
        <div aria-hidden="true" className="skeleton-row" key={index}>
          <span className="skeleton" />
          <span className="skeleton" />
          <span className="skeleton" />
          <span className="skeleton" />
        </div>
      ))}
    </div>
  );
}

export function EmptyState({
  title = "No results found",
  description,
  action,
}) {
  return (
    <div className="empty-state">
      <div aria-hidden="true" className="empty-icon">
        <Inbox size={23} />
      </div>
      <h3>{title}</h3>
      {description && <p>{description}</p>}
      {action}
    </div>
  );
}

export function ErrorState({
  title = "Something went wrong",
  message = "Please try again.",
  onRetry,
  retrying = false,
}) {
  return (
    <div className="error-state" role="alert">
      <AlertCircle aria-hidden="true" size={22} />
      <div>
        <strong>{title}</strong>
        <p>{message}</p>
      </div>
      {onRetry && (
        <Button
          disabled={retrying}
          loading={retrying}
          onClick={onRetry}
          variant="secondary"
        >
          Try again
        </Button>
      )}
    </div>
  );
}

export function Modal({
  open,
  title,
  description,
  children,
  onClose,
  footer,
  width = "medium",
}) {
  const titleId = useId();
  const descriptionId = useId();
  const dialogRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;

    const previouslyFocused = document.activeElement;
    const dialog = dialogRef.current;
    const focusableSelector =
      'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';
    const focusFirst = () => {
      const firstFocusable = dialog?.querySelector(focusableSelector);
      (firstFocusable ?? dialog)?.focus();
    };
    const handleKeyDown = (event) => {
      if (event.key === "Escape") {
        onClose?.();
        return;
      }

      if (event.key !== "Tab" || !dialog) return;
      const focusable = [...dialog.querySelectorAll(focusableSelector)];

      if (focusable.length === 0) {
        event.preventDefault();
        dialog.focus();
        return;
      }

      const firstFocusable = focusable[0];
      const lastFocusable = focusable[focusable.length - 1];

      if (event.shiftKey && document.activeElement === firstFocusable) {
        event.preventDefault();
        lastFocusable.focus();
      } else if (
        !event.shiftKey &&
        document.activeElement === lastFocusable
      ) {
        event.preventDefault();
        firstFocusable.focus();
      }
    };

    focusFirst();
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      if (previouslyFocused instanceof HTMLElement) previouslyFocused.focus();
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="modal-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose?.();
      }}
      role="presentation"
    >
      <section
        aria-describedby={description ? descriptionId : undefined}
        aria-labelledby={titleId}
        aria-modal="true"
        className={`modal modal-${width}`}
        ref={dialogRef}
        role="dialog"
        tabIndex={-1}
      >
        <header className="modal-header">
          <div>
            <h2 id={titleId}>{title}</h2>
            {description && <p id={descriptionId}>{description}</p>}
          </div>
          <button
            aria-label="Close dialog"
            className="icon-btn"
            onClick={onClose}
            type="button"
          >
            <X aria-hidden="true" size={20} />
          </button>
        </header>
        <div className="modal-body">{children}</div>
        {footer && <footer className="modal-footer">{footer}</footer>}
      </section>
    </div>
  );
}

export function SuccessMark({ label = "Success" }) {
  return (
    <div aria-label={label} className="success-mark" role="img">
      <Check aria-hidden="true" size={28} />
    </div>
  );
}

export function Toast({
  message,
  tone = "success",
  onClose,
  action,
}) {
  if (!message) return null;

  const isError = tone === "error";
  const Icon = isError ? AlertCircle : Check;

  return (
    <div
      className={`toast toast-${isError ? "error" : "success"}`}
      role={isError ? "alert" : "status"}
    >
      <Icon aria-hidden="true" size={17} />
      <span className="toast-message">{message}</span>
      {action}
      {onClose && (
        <button
          aria-label="Dismiss notification"
          className="icon-btn"
          onClick={onClose}
          type="button"
        >
          <X aria-hidden="true" size={16} />
        </button>
      )}
    </div>
  );
}