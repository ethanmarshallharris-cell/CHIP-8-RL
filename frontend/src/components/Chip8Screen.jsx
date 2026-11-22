import { forwardRef, useImperativeHandle, useRef } from "react";

export const WIDTH = 64;
export const HEIGHT = 32;

// A canvas that shows CHIP-8 frames. The parent calls screenRef.current.draw(pixels)
// with the 2,048 screen bytes whenever a new frame arrives.
const Chip8Screen = forwardRef(function Chip8Screen({ scale = 12, on = "#e8e8e8", off = "#111" }, ref) {
  const canvasRef = useRef(null);

  useImperativeHandle(ref, () => ({
    draw(pixels) {
      const ctx = canvasRef.current.getContext("2d");
      ctx.fillStyle = off;
      ctx.fillRect(0, 0, WIDTH * scale, HEIGHT * scale);
      ctx.fillStyle = on;
      for (let i = 0; i < WIDTH * HEIGHT; i++) {
        if (pixels[i]) {
          ctx.fillRect((i % WIDTH) * scale, Math.floor(i / WIDTH) * scale, scale, scale);
        }
      }
    },
    clear() {
      const ctx = canvasRef.current.getContext("2d");
      ctx.fillStyle = off;
      ctx.fillRect(0, 0, WIDTH * scale, HEIGHT * scale);
    },
  }));

  return <canvas ref={canvasRef} className="screen" width={WIDTH * scale} height={HEIGHT * scale} />;
});

export default Chip8Screen;
