const assert = require("node:assert/strict");
const test = require("node:test");

function loadRequest(responses) {
  const storage = { token: "expired-token" };
  const calls = {
    logins: 0,
    requests: [],
  };
  const app = { globalData: {} };

  global.getApp = () => app;
  global.wx = {
    getStorageSync(key) {
      return storage[key] || "";
    },
    setStorageSync(key, value) {
      storage[key] = value;
    },
    removeStorageSync(key) {
      delete storage[key];
    },
    login({ success }) {
      calls.logins += 1;
      success({ code: "renew-session-code" });
    },
    request(options) {
      calls.requests.push(options);
      const response = responses.shift();
      queueMicrotask(() => options.success(response));
    },
  };

  const modulePath = require.resolve("../utils/request.js");
  delete require.cache[modulePath];
  const { request } = require(modulePath);
  return { request, storage, app, calls };
}

test("expired villager session is renewed silently and the original request is retried once", async () => {
  const profile = { id: 36, auth_status: "verified", realname_status: "verified" };
  const runtime = loadRequest([
    { statusCode: 401, data: { detail: "token_expired" } },
    { statusCode: 200, data: { token: "renewed-token", user: profile } },
    { statusCode: 200, data: profile },
  ]);

  const result = await runtime.request({ path: "/auth/me" });

  assert.deepEqual(result, profile);
  assert.equal(runtime.calls.logins, 1);
  assert.equal(runtime.calls.requests.length, 3);
  assert.match(runtime.calls.requests[1].url, /\/auth\/wechat-login$/);
  assert.match(runtime.calls.requests[2].url, /\/auth\/me$/);
  assert.equal(runtime.calls.requests[2].header["X-Token"], "renewed-token");
  assert.equal(runtime.storage.token, "renewed-token");
  assert.deepEqual(runtime.app.globalData.userProfile, profile);
});

test("explicit logout never creates a replacement session", async () => {
  const runtime = loadRequest([
    { statusCode: 401, data: { detail: "token_expired" } },
  ]);

  await assert.rejects(
    runtime.request({
      path: "/auth/logout",
      method: "POST",
      skipAuthRecovery: true,
    }),
    { detail: "token_expired" }
  );

  assert.equal(runtime.calls.logins, 0);
  assert.equal(runtime.calls.requests.length, 1);
});

test("a retried request cannot start a second recovery loop", async () => {
  const runtime = loadRequest([
    { statusCode: 401, data: { detail: "token_expired" } },
    {
      statusCode: 200,
      data: { token: "renewed-token", user: { id: 36, auth_status: "verified" } },
    },
    { statusCode: 401, data: { detail: "invalid_token" } },
  ]);

  await assert.rejects(runtime.request({ path: "/auth/me" }), { detail: "invalid_token" });

  assert.equal(runtime.calls.logins, 1);
  assert.equal(runtime.calls.requests.length, 3);
});
