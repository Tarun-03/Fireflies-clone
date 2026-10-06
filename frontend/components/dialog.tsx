"use client";
import * as RadixDialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
export function Dialog({
  title,
  description,
  open,
  onOpenChange,
  children,
  wide = false,
  drawer = false,
}: {
  title: string;
  description?: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  children: React.ReactNode;
  wide?: boolean;
  drawer?: boolean;
}) {
  return (
    <RadixDialog.Root open={open} onOpenChange={onOpenChange}>
      <RadixDialog.Portal>
        <RadixDialog.Overlay className="dialog-overlay" />
        <RadixDialog.Content
          className={`dialog ${wide ? "wide" : ""} ${drawer ? "drawer" : ""}`}
        >
          <div className="dialog-heading">
            <RadixDialog.Title>{title}</RadixDialog.Title>
            <RadixDialog.Close
              className="icon-button"
              aria-label="Close dialog"
            >
              <X size={18} />
            </RadixDialog.Close>
          </div>
          <RadixDialog.Description
            className={description ? "muted" : "sr-only"}
          >
            {description ?? title}
          </RadixDialog.Description>
          {children}
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  );
}
export function ErrorNotice({ error }: { error: Error | null }) {
  return error ? (
    <p role="alert" className="error-notice">
      {error.message}
    </p>
  ) : null;
}
