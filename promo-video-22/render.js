// node render.js preview 1,5,9   -> build/prev_<t>.png
// node render.js video           -> build/video.mp4 (silent, 30fps)
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const http = require('http'), fs = require('fs'), path = require('path');
const TL = JSON.parse(fs.readFileSync(path.join(__dirname, 'build/timeline.json'), 'utf8'));
const FPS = 30, DUR = TL.dur;
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json' };
const srv = http.createServer((q, r) => { const f = path.join(__dirname, decodeURIComponent(q.url.split('?')[0]));
  fs.readFile(f, (e, d) => { if (e) { r.writeHead(404); return r.end(); } r.writeHead(200, { 'Content-Type': MIME[path.extname(f)] || 'application/octet-stream' }); r.end(d); }); });
(async () => {
  await new Promise(r => srv.listen(0, r)); const port = srv.address().port;
  const mode = process.argv[2] || 'preview';
  const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on('pageerror', e => console.error('PAGE ERROR', e.message)); page.on('console', m => { if (m.type() === 'error') console.error('console:', m.text()); });
  await page.addInitScript(tl => { window.TIMELINE = tl; }, TL);
  await page.goto(`http://127.0.0.1:${port}/index.html`);
  await page.waitForFunction(() => window.READY === true, null, { timeout: 60000 });
  await page.evaluate(() => document.fonts.ready);
  const frame = async t => { await page.evaluate(t => render(t), t); };
  if (mode === 'preview') {
    for (const t of (process.argv[3] || '1').split(',').map(Number)) { await frame(t); await page.screenshot({ path: `build/prev_${t}.png` }); }
  } else {
    const ff = spawn('ffmpeg', ['-y', '-v', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-preset', 'medium', '-crf', '18', 'build/video.mp4'], { stdio: ['pipe', 'inherit', 'inherit'] });
    const N = Math.round(FPS * DUR);
    for (let f = 0; f < N; f++) { await frame(f / FPS); const buf = await page.screenshot({ type: 'jpeg', quality: 94 });
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r)); if (f % 60 === 0) console.log(`frame ${f}/${N}`); }
    ff.stdin.end(); await new Promise(r => ff.on('close', r));
  }
  await browser.close(); srv.close();
})();
