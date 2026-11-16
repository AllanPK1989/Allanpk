// Optional: serve the Firebase JS SDK from node_modules instead of
// www.gstatic.com. Only needed on networks that block the CDN; enable with
// LOCAL_FIREBASE_SDK=1 after `npm install` (firebase is a devDependency).
const fs = require('fs');
const path = require('path');

module.exports = async function interceptFirebase(page) {
  if (!process.env.LOCAL_FIREBASE_SDK) return;
  const root = path.join(__dirname, 'node_modules', 'firebase');
  await page.route('https://www.gstatic.com/firebasejs/**', async (route) => {
    const url = new URL(route.request().url());
    const file = path.join(root, path.basename(url.pathname));
    if (fs.existsSync(file)) {
      await route.fulfill({
        status: 200,
        contentType: 'application/javascript',
        headers: { 'access-control-allow-origin': '*' },
        body: fs.readFileSync(file),
      });
    } else {
      console.log('[intercept] missing', url.pathname);
      await route.abort();
    }
  });
};
