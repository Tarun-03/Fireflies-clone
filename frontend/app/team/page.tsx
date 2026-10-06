import { Plug } from "lucide-react";
export default function Page() {
  return (
    <div className="empty-state">
      <Plug size={32} />
      <span className="subtle-badge">Coming soon</span>
      <h1>Team</h1>
      <p>
        Sharing and team collaboration are coming soon. Your demo workspace is
        private.
      </p>
    </div>
  );
}
