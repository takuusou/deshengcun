// Production is the default tracked/uploaded configuration. Local work may
// create the ignored config/env.local.js with { target: "local", ... }.
const DEFAULT_TARGET = "production";
let localConfig = null;
try {
  localConfig = require("./env.local");
} catch (err) {
  localConfig = null;
}
const TARGET = localConfig && localConfig.target === "local" ? "local" : DEFAULT_TARGET;

const ENVIRONMENTS = {
  production: {
    apiBase: "https://api.example.invalid/api/v1",
    cloudbase: {
      enabled: true,
      envId: "YOUR_CLOUDBASE_ENV_ID",
      service: "fastapi-api",
      publicBaseUrl: "https://api.example.invalid",
    },
  },
  local: localConfig || {},
};

const active = ENVIRONMENTS[TARGET] || ENVIRONMENTS.production;

module.exports = {
  target: TARGET,
  ...active,
};
