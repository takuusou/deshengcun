import { createApp } from "vue";
import { createPinia } from "pinia";

import App from "./App.vue";
import router from "./router";
import { clearSuccessToast } from "./utils/success-toast";
import "./styles.css";

const app = createApp(App);

app.use(createPinia());
app.use(router);
router.afterEach(() => clearSuccessToast());
app.mount("#app");
