import { Link } from "react-router"

export default function NotFoundPage() {
  return (
    <section className="not-found-page">
      <p className="eyebrow">404 · PAGE NOT FOUND</p>
      <h1>This page isn't here</h1>
      <p>The link may be incorrect, or the page may have moved.</p>
      <Link className="btn btn-primary" to="/inventory">
        Return to inventory
      </Link>
    </section>
  )
}
