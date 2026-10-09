/** @jest-environment node */

const fs = require("fs");
const os = require("os");
const path = require("path");
const { execFileSync } = require("child_process");

test("the locked toolchain contains no vulnerable sprintf-js package", () => {
  const lock = require("../../package-lock.json");
  expect(Object.keys(lock.packages).filter(name => /(^|\/)node_modules\/sprintf-js$/.test(name))).toEqual([]);
});

test("Istanbul still loads YAML inheritance and normalizes coverage options", async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "dr-download-nyc-"));
  try {
    fs.writeFileSync(path.join(root, "base.yml"), "all: true\ninclude:\n  - src/**/*.js\n");
    fs.writeFileSync(path.join(root, ".nycrc.yml"), "extends: ./base.yml\ncheck-coverage: true\nlines: 80\n");
    const { loadNycConfig } = require("@istanbuljs/load-nyc-config");
    const config = await loadNycConfig({ cwd: root });
    expect(config).toMatchObject({ all: true, include: ["src/**/*.js"], checkCoverage: true, lines: 80 });
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test("electron-builder's downloader still routes HTTP through its configured proxy", () => {
  // Bootstrap changes global HTTP agents, so exercise the real consumer in a separate process.
  const script = `
    const assert = require('node:assert/strict');
    const http = require('node:http');
    const builder = require.resolve('app-builder-lib');
    const downloader = require.resolve('@electron/get', { paths: [builder] });
    const proxy = http.createServer((request, response) => {
      assert.equal(request.url, 'http://dr-download.invalid/runtime.zip');
      response.end('proxied-runtime');
    });
    proxy.listen(0, '127.0.0.1', () => {
      process.env.GLOBAL_AGENT_HTTP_PROXY = 'http://127.0.0.1:' + proxy.address().port;
      process.env.GLOBAL_AGENT_NO_PROXY = '';
      require(downloader).initializeProxy();
      http.get('http://dr-download.invalid/runtime.zip', response => {
        let body = '';
        response.on('data', chunk => { body += chunk; });
        response.on('end', () => {
          assert.equal(body, 'proxied-runtime');
          proxy.close();
        });
      }).on('error', error => { console.error(error); process.exit(1); });
    });
  `;
  execFileSync(process.execPath, ["-e", script], { timeout: 10000, stdio: "pipe" });
});
