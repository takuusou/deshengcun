const assert = require("node:assert/strict");
const test = require("node:test");

function stubModule(path, exports) {
  require.cache[require.resolve(path)] = {
    id: require.resolve(path),
    filename: require.resolve(path),
    loaded: true,
    exports,
  };
}

function loadEntryPage(requestError) {
  let pageDefinition = null;
  const calls = { toasts: [] };

  global.Page = (definition) => {
    pageDefinition = definition;
  };
  global.wx = {
    showToast(options) {
      calls.toasts.push(options);
    },
  };

  stubModule("../utils/request.js", {
    request: async () => Promise.reject(requestError),
  });
  stubModule("../utils/auth.js", {
    getToken: () => "existing-token",
    setToken() {},
    getUserProfile: () => ({ id: 36, auth_status: "verified" }),
    setUserProfile() {},
    clearSession() {},
    revokeServerSession: async () => {},
  });
  stubModule("../utils/messages.js", {
    getErrorMessage: () => "网络暂时不可用",
  });
  stubModule("../utils/phone.js", {
    formatPhoneDisplay: (value) => value,
  });

  const modulePath = require.resolve("../pages/entry/entry.js");
  delete require.cache[modulePath];
  require(modulePath);
  return { pageDefinition, calls };
}

test("a temporary profile refresh failure keeps the existing resident session", async () => {
  const { pageDefinition, calls } = loadEntryPage({ detail: "network_unavailable" });
  let resets = 0;
  const context = {
    resetResidentSession() {
      resets += 1;
    },
    updateFromProfile() {},
  };

  await pageDefinition.refreshProfile.call(context);

  assert.equal(resets, 0);
  assert.equal(calls.toasts.length, 1);
});

test("a confirmed invalid token clears the resident session", async () => {
  const { pageDefinition } = loadEntryPage({ detail: "invalid_token" });
  let resets = 0;
  const context = {
    resetResidentSession() {
      resets += 1;
    },
    updateFromProfile() {},
  };

  await pageDefinition.refreshProfile.call(context);

  assert.equal(resets, 1);
});
