import AssistantChat from "../components/AssistantChat";
import { PageHeader } from "../components/ui";

export default function AssistantPage() {
  return (
    <section className="assistant-page">
      <PageHeader
        description="Ask questions about recorded stock and inventory movements."
        eyebrow="ADMIN WORKSPACE"
        title="Assistance"
      />
      <AssistantChat />
    </section>
  );
}