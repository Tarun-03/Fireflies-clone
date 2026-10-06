import { Plug } from "lucide-react";
export default function Page() {
  return (
    <div className="empty-state">
      <Plug size={32} />
      <span className="subtle-badge">Coming soon</span>
      <h1>Meeting bot</h1>
      <p>
        Live meeting capture and transcription are coming soon. You can create a
        meeting from a transcript instead.
      </p>
    </div>
  );
}
