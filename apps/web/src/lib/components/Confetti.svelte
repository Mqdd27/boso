<script lang="ts">
	// A short burst of confetti on a canvas over the page. Skipped with reduced motion.
	let canvas: HTMLCanvasElement | undefined = $state();

	$effect(() => {
		if (!canvas || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
		const ctx = canvas.getContext('2d');
		if (!ctx) return;
		const css = getComputedStyle(document.documentElement);
		const colors = [
			'--green-fill',
			'--blue-fill',
			'--gold-fill',
			'--purple-fill',
			'--red-fill'
		].map((v) => css.getPropertyValue(v).trim());
		const w = (canvas.width = innerWidth);
		const h = (canvas.height = innerHeight);
		const bits = Array.from({ length: 90 }, (_, i) => ({
			x: w / 2 + (Math.random() - 0.5) * w * 0.3,
			y: h * 0.35,
			vx: (Math.random() - 0.5) * 14,
			vy: -Math.random() * 14 - 4,
			r: Math.random() * Math.PI,
			vr: (Math.random() - 0.5) * 0.4,
			size: 6 + Math.random() * 6,
			color: colors[i % colors.length]
		}));
		const end = performance.now() + 2200;
		let frame = 0;
		const draw = (now: number) => {
			ctx.clearRect(0, 0, w, h);
			for (const b of bits) {
				b.vy += 0.45;
				b.vx *= 0.99;
				b.x += b.vx;
				b.y += b.vy;
				b.r += b.vr;
				ctx.save();
				ctx.translate(b.x, b.y);
				ctx.rotate(b.r);
				ctx.globalAlpha = Math.max(0, Math.min(1, (end - now) / 600));
				ctx.fillStyle = b.color;
				ctx.fillRect(-b.size / 2, -b.size / 4, b.size, b.size / 2);
				ctx.restore();
			}
			if (now < end) frame = requestAnimationFrame(draw);
			else ctx.clearRect(0, 0, w, h);
		};
		frame = requestAnimationFrame(draw);
		return () => cancelAnimationFrame(frame);
	});
</script>

<canvas bind:this={canvas} class="pointer-events-none fixed inset-0 z-30" aria-hidden="true"
></canvas>
