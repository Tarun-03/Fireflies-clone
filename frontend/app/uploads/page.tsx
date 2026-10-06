import { Suspense } from "react";
import { Library } from "@/features/library/library";
export default function Page() {
  return (
    <Suspense fallback={<p>Loading uploads…</p>}>
      <Library uploads />
    </Suspense>
  );
}
