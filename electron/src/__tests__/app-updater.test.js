/** @jest-environment node */

const { hasActiveDownloads } = require("../../app-updater");

test("application updates wait for active downloads", () => {
  expect(hasActiveDownloads([{ status: "downloading" }])).toBe(true);
  expect(hasActiveDownloads([{ status: "completed" }, { status: "failed" }])).toBe(false);
});

