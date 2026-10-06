"use client";
export default function ErrorPage({
  reset,
}: {
  error: Error;
  reset: () => void;
}) {
  return (
    <div className="empty-state">
      <h1>Something went wrong</h1>
      <p>
        Your saved work is still in your workspace. Please try loading this page
        again.
      </p>
      <button onClick={reset}>Try again</button>
    </div>
  );
}
