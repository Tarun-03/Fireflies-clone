export async function download(path: string, filename: string) {
  const response = await fetch(`/api/v1/${path}`, { cache: "no-store" });
  if (!response.ok) {
    const body = await response.json();
    throw new Error(body.error?.message ?? "Download failed. Please retry.");
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
