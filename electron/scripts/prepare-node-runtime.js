const fs = require("fs");
const path = require("path");

if (process.platform !== "win32") throw new Error("Windows Node runtime packaging requires Windows");

const destination = path.resolve(__dirname, "..", "resources", "node", "node.exe");
fs.mkdirSync(path.dirname(destination), { recursive: true });
fs.copyFileSync(process.execPath, destination);
console.log(`Prepared Node runtime: ${destination}`);
