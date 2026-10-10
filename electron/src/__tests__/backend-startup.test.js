/** @jest-environment node */
const { waitForBackend } = require("../../backend-client");

beforeEach(() => { jest.useFakeTimers(); global.fetch = jest.fn(); });
afterEach(() => { jest.useRealTimers(); delete global.fetch; });
const running = { exitCode: null, signalCode: null };

test("waits for a healthy first startup that takes longer than fifteen seconds", async () => {
  const started = Date.now();
  fetch.mockImplementation(async () => ({ ok: Date.now() - started >= 30000 }));
  const result = expect(waitForBackend("http://localhost:1234", "test-token", running)).resolves.toBeUndefined();
  await jest.advanceTimersByTimeAsync(30000);
  await result;
  expect(fetch).toHaveBeenLastCalledWith("http://localhost:1234/health", expect.objectContaining({ headers: { "X-Dr-Download-Token": "test-token" } }));
});

test("stops waiting as soon as the backend process exits", async () => {
  fetch.mockResolvedValue({ ok: true });
  await expect(waitForBackend("http://localhost:1234", "test-token", { exitCode: 1, signalCode: null })).rejects.toThrow("Backend exited before becoming ready");
  expect(fetch).not.toHaveBeenCalled();
});

test("rejects an unready backend after the bounded startup deadline", async () => {
  fetch.mockResolvedValue({ ok: false });
  const started = Date.now();
  let finished;
  const operation = waitForBackend("http://localhost:1234", "test-token", running).finally(() => { finished = Date.now() - started; });
  const result = expect(operation).rejects.toThrow("Backend did not start in time");
  await jest.advanceTimersByTimeAsync(120000);
  await result;
  expect(finished).toBe(120000);
  expect(fetch.mock.calls[0][1].signal).toBeInstanceOf(AbortSignal);
});
