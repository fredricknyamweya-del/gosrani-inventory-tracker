import ThemeToggle from "../components/ThemeToggle";
import { ThemeProvider } from "../context/ThemeContext";

export default function App() {
  return (
    <ThemeProvider>
      <main className="theme-demo">
        <ThemeToggle />
        <h1>Gosrani Wholesalers Limited</h1>
      </main>
    </ThemeProvider>
  );
}