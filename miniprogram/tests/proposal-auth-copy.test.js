const assert = require("node:assert/strict");
const test = require("node:test");

const EXPECTED_AUTH_MODAL = {
  title: "提交需登记身份信息",
  content: "提交前请先登录并完成基础实名登记。",
  confirmText: "去登录",
  cancelText: "先返回",
};

function loadPage(modulePath) {
  let pageDefinition = null;
  const modals = [];
  const stubs = new Map([
    [require.resolve("../utils/request.js"), { request: async () => [] }],
    [require.resolve("../utils/auth.js"), { getToken: () => "" }],
    [require.resolve("../utils/messages.js"), { getErrorMessage: () => "请求失败" }],
    [require.resolve("../utils/share.js"), {
      showDefaultShareMenu() {},
      buildShareAppMessage: () => ({}),
      buildShareTimeline: () => ({}),
    }],
  ]);
  const resolvedAccessPath = require.resolve("../utils/access.js");
  const resolvedModulePath = require.resolve(modulePath);
  const managedPaths = [...stubs.keys(), resolvedAccessPath, resolvedModulePath];
  const previousCache = new Map(managedPaths.map((resolvedPath) => [resolvedPath, require.cache[resolvedPath]]));

  for (const [resolvedPath, exports] of stubs) {
    require.cache[resolvedPath] = {
      id: resolvedPath,
      filename: resolvedPath,
      loaded: true,
      exports,
    };
  }
  delete require.cache[resolvedAccessPath];
  delete require.cache[resolvedModulePath];

  global.Page = (definition) => {
    pageDefinition = definition;
  };
  global.wx = {
    navigateTo() {},
    showToast() {},
    showModal(options) {
      modals.push({
        title: options.title,
        content: options.content,
        confirmText: options.confirmText,
        cancelText: options.cancelText,
      });
      options.success({ confirm: false });
    },
  };

  require(resolvedModulePath);

  for (const resolvedPath of managedPaths) {
    const previous = previousCache.get(resolvedPath);
    if (previous) {
      require.cache[resolvedPath] = previous;
    } else {
      delete require.cache[resolvedPath];
    }
  }

  return { pageDefinition, modals };
}

test("proposal entry uses the standard identity registration prompt", async () => {
  const { pageDefinition, modals } = loadPage("../pages/service/service.js");

  await pageDefinition.tapCivic.call({}, {
    currentTarget: { dataset: { key: "proposal" } },
  });

  assert.deepEqual(modals, [EXPECTED_AUTH_MODAL]);
});

test("proposal submission uses the standard identity registration prompt", async () => {
  const { pageDefinition, modals } = loadPage("../pages/services/proposal/proposal.js");
  const context = {
    data: { content: "村务建议", submitting: false },
    setData(update) {
      Object.assign(this.data, update);
    },
  };

  await pageDefinition.submitProposal.call(context);

  assert.deepEqual(modals, [EXPECTED_AUTH_MODAL]);
});
