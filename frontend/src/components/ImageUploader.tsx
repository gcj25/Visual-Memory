import { useEffect, useId, useState } from "react";
import { ImagePlus, X } from "lucide-react";

const MAX_BYTES = 10 * 1024 * 1024;

interface Props { label: string; hint: string; file: File | null; onChange: (f: File | null) => void; disabled?: boolean }

export default function ImageUploader({ label, hint, file, onChange, disabled }: Props) {
  const id = useId();
  const [preview, setPreview] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!file) { setPreview(null); return; }
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  function pick(f: File | undefined) {
    if (!f) return;
    if (!f.type.startsWith("image/")) { setError("That file is not an image."); return; }
    if (f.size > MAX_BYTES) { setError("Images must be 10 MB or smaller."); return; }
    setError(null);
    onChange(f);
  }

  return (
    <div className="panel p-4">
      <div className="mb-2 flex items-baseline justify-between">
        <label htmlFor={id} className="text-sm font-semibold">{label}</label>
        {file && (
          <button type="button" className="inline-flex items-center gap-1 text-xs text-mist-500 hover:text-mist-100"
                  onClick={() => { onChange(null); setError(null); }} disabled={disabled}>
            <X size={14} aria-hidden /> Remove
          </button>
        )}
      </div>
      <label htmlFor={id}
             onDragOver={(e) => e.preventDefault()}
             onDrop={(e) => { e.preventDefault(); if (!disabled) pick(e.dataTransfer.files[0]); }}
             className="flex aspect-[4/3] cursor-pointer items-center justify-center overflow-hidden rounded border border-dashed border-ink-600 bg-ink-900 hover:border-accent/60">
        {preview ? (
          <img src={preview} alt={`${label} preview`} className="h-full w-full object-contain" />
        ) : (
          <span className="flex flex-col items-center gap-2 px-4 text-center text-sm text-mist-500">
            <ImagePlus size={28} aria-hidden />
            {hint}
          </span>
        )}
      </label>
      <input id={id} type="file" accept="image/jpeg,image/png,image/bmp,image/webp,image/tiff" className="sr-only"
             disabled={disabled} onChange={(e) => { pick(e.target.files?.[0]); e.target.value = ""; }} />
      <p className="mt-2 truncate text-xs text-mist-500">{file ? `${file.name} · ${(file.size / 1024).toFixed(0)} KB` : "JPEG, PNG, BMP, WEBP or TIFF · up to 10 MB"}</p>
      {error && <p role="alert" className="mt-1 text-xs text-gone">{error}</p>}
    </div>
  );
}
