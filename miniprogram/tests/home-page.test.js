const assert = require("node:assert/strict");
const test = require("node:test");

function loadHomePage() {
  let pageDefinition = null;
  const calls = {
    dialed: [],
    miniPrograms: [],
    navigated: [],
    toasts: [],
  };

  global.getApp = () => ({ globalData: {} });
  global.Page = (definition) => {
    pageDefinition = definition;
  };
  global.wx = {
    makePhoneCall({ phoneNumber }) {
      calls.dialed.push(phoneNumber);
    },
    navigateTo({ url }) {
      calls.navigated.push(url);
    },
    navigateToMiniProgram(options) {
      calls.miniPrograms.push(options);
    },
    showToast(options) {
      calls.toasts.push(options);
    },
  };

  const modulePath = require.resolve("../pages/home/home.js");
  delete require.cache[modulePath];
  require(modulePath);

  return { pageDefinition, calls };
}

function createPageContext(pageDefinition) {
  return {
    data: JSON.parse(JSON.stringify(pageDefinition.data)),
    setData(update) {
      Object.assign(this.data, update);
    },
    findMiniProgramLink: pageDefinition.findMiniProgramLink,
  };
}

test("phone button dials the number currently shown", () => {
  const { pageDefinition, calls } = loadHomePage();
  const context = createPageContext(pageDefinition);
  context.data.phoneCurrent = 3;

  pageDefinition.callCurrentPhone.call(context);

  assert.deepEqual(calls.dialed, ["119"]);
});

test("annual assistance entry directly opens the target mini program", () => {
  const { pageDefinition, calls } = loadHomePage();
  const context = createPageContext(pageDefinition);
  const annualReview = context.data.miniProgramLinks[4];

  assert.equal(annualReview.title, "奖扶年审");
  pageDefinition.openMiniProgramLink.call(context, {
    currentTarget: { dataset: { key: annualReview.key } },
  });

  assert.equal(calls.miniPrograms.length, 1);
  assert.equal(calls.miniPrograms[0].appId, "wx0000000000000000");
  assert.deepEqual(calls.navigated, []);
});

test("rural land contract entry directly opens the target mini program", () => {
  const { pageDefinition, calls } = loadHomePage();
  const context = createPageContext(pageDefinition);
  const ruralLandContract = context.data.miniProgramLinks[2];

  assert.equal(ruralLandContract.title, "土地承包");
  pageDefinition.openMiniProgramLink.call(context, {
    currentTarget: { dataset: { key: ruralLandContract.key } },
  });

  assert.equal(calls.miniPrograms.length, 1);
  assert.equal(calls.miniPrograms[0].appId, "wx0000000000000000");
  assert.deepEqual(calls.toasts, []);
});
