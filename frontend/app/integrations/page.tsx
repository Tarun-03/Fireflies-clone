import { Plug } from "lucide-react";
export default function Page() {
  return (
    <div className="empty-state">
      <Plug size={32} />
      <span className="subtle-badge">Coming soon</span>
      <h1>Integrations</h1>
      <p>Connections to external apps are coming soon.</p>
    </div>
  );
}
