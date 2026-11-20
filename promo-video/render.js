// Usage: node render.js preview  -> writes a few PNG frames
//        node render.js video    -> pipes 30fps frames into ffmpeg (build/video.mp4, silent)
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
const FPS = 30, DUR = 15;
(async () => {
  const mode = process.argv[2] || 'preview';
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await page.goto('file://' + path.join(__dirname, 'scene.html'));
  await page.evaluate(() => document.fonts.ready);
  if (mode === 'preview') {
    for (const t of (process.argv[3] || '1.2,2.6,5.6,9.5,13.5').split(',').map(Number)) {
      await page.evaluate(t => render(t), t);
      await page.screenshot({ path: `build/prev_${t}.png` });
    }
  } else {
    const ff = spawn('ffmpeg', ['-y', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
      '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-preset', 'medium', '-crf', '18', 'build/video.mp4'], { stdio: ['pipe', 'ignore', 'inherit'] });
    for (let f = 0; f < FPS * DUR; f++) {
      await page.evaluate(t => render(t), f / FPS);
      const buf = await page.screenshot({ type: 'jpeg', quality: 95 });
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    }
    ff.stdin.end();
    await new Promise(r => ff.on('close', r));
  }
  await browser.close();
})();
