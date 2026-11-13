import { ArrowLeft } from "lucide-react";
import { useNavigate } from "react-router";
import AssistantChat from "../components/AssistantChat";
import { Button, PageHeader } from "../components/ui";

export default function AssistantPage() {
  const navigate = useNavigate();

  return (
    <section className="assistant-page">
      <PageHeader
        actions={
          <Button
            onClick={() => {
              if (window.history.state?.idx > 0) {
                navigate(-1);
              } else {
                navigate("/inventory");
              }
            }}
            variant="secondary"
          >
            <ArrowLeft aria-hidden="true" size={16} />
            Back
          </Button>
        }
        description="Ask questions about recorded stock and inventory movements."
        eyebrow="ADMIN WORKSPACE"
        title="Assistant"
      />
      <AssistantChat />
    </section>
  );
}