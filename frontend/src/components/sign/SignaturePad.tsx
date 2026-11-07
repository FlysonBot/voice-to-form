import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react';

export interface SignaturePadHandle {
  clear: () => void;
  /** base64 PNG without the data: prefix, or null if empty */
  toBase64: () => string | null;
}

/** Finger / mouse signature on a canvas. No dependencies. */
const SignaturePad = forwardRef<SignaturePadHandle, { onChange?: (hasInk: boolean) => void; label: string }>(
  function SignaturePad({ onChange, label }, ref) {
    const canvas = useRef<HTMLCanvasElement>(null);
    const drawing = useRef(false);
    const last = useRef<{ x: number; y: number } | null>(null);
    const [hasInk, setHasInk] = useState(false);

    // Match the canvas to its on-screen size (sharp on retina screens)
    useEffect(() => {
      const c = canvas.current!;
      const ratio = window.devicePixelRatio || 1;
      const { width, height } = c.getBoundingClientRect();
      c.width = width * ratio;
      c.height = height * ratio;
      const ctx = c.getContext('2d')!;
      ctx.scale(ratio, ratio);
      ctx.lineWidth = 2.5;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      ctx.strokeStyle = '#111827';
    }, []);

    const point = (e: React.PointerEvent) => {
      const r = canvas.current!.getBoundingClientRect();
      return { x: e.clientX - r.left, y: e.clientY - r.top };
    };

    const setInk = (v: boolean) => {
      setHasInk(v);
      onChange?.(v);
    };

    useImperativeHandle(ref, () => ({
      clear: () => {
        const c = canvas.current!;
        c.getContext('2d')!.clearRect(0, 0, c.width, c.height);
        setInk(false);
      },
      toBase64: () => (hasInk ? canvas.current!.toDataURL('image/png').split(',')[1] : null),
    }));

    return (
      <canvas
        ref={canvas}
        role="img"
        aria-label={label}
        className="h-48 w-full touch-none rounded-xl bg-white ring-2 ring-stone-300"
        onPointerDown={(e) => {
          drawing.current = true;
          last.current = point(e);
          canvas.current!.setPointerCapture(e.pointerId);
        }}
        onPointerMove={(e) => {
          if (!drawing.current || !last.current) return;
          const p = point(e);
          const ctx = canvas.current!.getContext('2d')!;
          ctx.beginPath();
          ctx.moveTo(last.current.x, last.current.y);
          ctx.lineTo(p.x, p.y);
          ctx.stroke();
          last.current = p;
          if (!hasInk) setInk(true);
        }}
        onPointerUp={() => {
          drawing.current = false;
          last.current = null;
        }}
        onPointerCancel={() => {
          drawing.current = false;
          last.current = null;
        }}
      />
    );
  },
);

export default SignaturePad;
