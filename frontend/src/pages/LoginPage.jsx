import { useState } from "react";
import { ArrowRight, Eye, EyeOff, ShieldCheck } from "lucide-react";
import { Link, Navigate, useLocation, useNavigate } from "react-router";
import { Button, Field, Input } from "../components/ui";
import { useAuth } from "../context/AuthContext";

export default function LoginPage() {
  const { user, loading, login } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  if (loading) return <div className="login-loading" role="status">Checking your session…</div>;
  if (user) return <Navigate replace to="/inventory" />;

  const destination = location.state?.from?.pathname ?? "/inventory";

  async function signIn(credentials) {
    setError("");
    setSubmitting(true);
    try {
      await login(credentials);
      navigate(destination, { replace: true });
    } catch (loginError) {
      setError(loginError.message || "Unable to sign in. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  function handleSubmit(event) {
    event.preventDefault();
    if (!email.trim() || !password) {
      setError("Enter your email address and password.");
      return;
    }
    signIn({ email, password });
  }

  return (
    <main className="login-page">
      <section aria-label="About Gosrani Wholesalers" className="login-brand-panel">
        <div className="login-brand-visual">
          <Link aria-label="Gosrani Wholesalers home" className="login-brand" to="/login">
            <img alt="Gosrani Wholesalers Limited" className="login-brand-logo" src="/gw-logo-login.png" />
          </Link>
          <img
            alt="Gosrani Wholesalers storefront"
            className="login-brand-photo"
            src="/Gosrani Frontend Shop Image.jpeg"
          />
        </div>
        <div className="login-brand-copy">
          <div className="login-kicker"><span /> INVENTORY MANAGEMENT</div>
          <h1>Everything in stock. Everything in sync.</h1>
          <p>
            Keep your inventory accurate and your team connected with one
            reliable workspace.
          </p>
        </div>
        <div className="login-brand-footer">
          <ShieldCheck aria-hidden="true" size={17} />
          <span>Secure access for your team</span>
        </div>
      </section>

      <section aria-labelledby="login-heading" className="login-form-panel">
        <div className="login-form-wrap">
          <div className="login-mobile-brand">
            <img alt="Gosrani Wholesalers Limited" className="login-brand-logo" src="/gw-logo-login.png" />
          </div>
          <div className="login-heading">
            <p className="eyebrow">WELCOME BACK</p>
            <h2 id="login-heading">Sign in to your account</h2>
            <p>Enter your work email and password to continue.</p>
          </div>

          <form className="login-form" onSubmit={handleSubmit}>
            {error && <div className="login-error" role="alert">{error}</div>}
            <Field label="Email address" required>
              <Input
                autoComplete="username"
                autoFocus
                onChange={(event) => {
                  setEmail(event.target.value);
                }}
                placeholder="name@gosrani.co.ke"
                type="email"
                value={email}
              />
            </Field>
            <Field id="login-password-input" label="Password" required>
              <div className="login-password">
                <Input
                  autoComplete="current-password"
                  id="login-password-input"
                  onChange={(event) => {
                    setPassword(event.target.value);
                  }}
                  placeholder="Enter your password"
                  type={showPassword ? "text" : "password"}
                  value={password}
                />
                <button
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  className="login-password-toggle"
                  onClick={() => setShowPassword((visible) => !visible)}
                  type="button"
                >
                  {showPassword
                    ? <EyeOff aria-hidden="true" size={17} />
                    : <Eye aria-hidden="true" size={17} />}
                </button>
              </div>
            </Field>
            <Button className="login-submit" loading={submitting} type="submit">
              Sign in <ArrowRight aria-hidden="true" size={17} />
            </Button>
          </form>

          <p className="login-copyright">
            © {new Date().getFullYear()} Gosrani Wholesalers Limited
          </p>
        </div>
      </section>
    </main>
  );
}