import { Suspense } from "react";
import { Notebook } from "@/features/notebook/notebook";
export default async function MeetingPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <Suspense fallback={<p>Opening notebook…</p>}>
      <Notebook id={id} />
    </Suspense>
  );
}
