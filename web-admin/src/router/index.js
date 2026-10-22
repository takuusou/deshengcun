import { createRouter, createWebHistory } from "vue-router";

import AdminLayout from "../layouts/AdminLayout.vue";
import DashboardView from "../views/dashboard/DashboardView.vue";
import LoginView from "../views/auth/LoginView.vue";
import SecuritySetupView from "../views/auth/SecuritySetupView.vue";
import PublishingHubView from "../views/notices/PublishingHubView.vue";
import TaskHubView from "../views/requests/TaskHubView.vue";
import SystemAdminView from "../views/system/SystemAdminView.vue";
import VillagerDataView from "../views/villagers/VillagerDataView.vue";
import { ensureAuthGuard } from "./guards";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: "/login",
      name: "login",
      component: LoginView,
      meta: { public: true },
    },
    {
      path: "/security-setup",
      name: "security-setup",
      component: SecuritySetupView,
      meta: { requiresAuth: true },
    },
    {
      path: "/",
      component: AdminLayout,
      meta: { requiresAuth: true },
      children: [
        {
          path: "",
          name: "dashboard",
          component: DashboardView,
          meta: { requiresAuth: true },
        },
        {
          path: "requests",
          name: "requests",
          component: TaskHubView,
          meta: { requiresAuth: true },
        },
        {
          path: "gov-applications",
          name: "gov-applications",
          component: TaskHubView,
          meta: { requiresAuth: true },
        },
        {
          path: "notices",
          name: "notices",
          component: PublishingHubView,
          meta: { requiresAuth: true },
        },
        {
          path: "volunteer-events",
          name: "volunteer-events",
          component: PublishingHubView,
          meta: { requiresAuth: true },
        },
        {
          path: "training-programs",
          name: "training-programs",
          component: PublishingHubView,
          meta: { requiresAuth: true },
        },
        {
          path: "open",
          name: "open",
          component: PublishingHubView,
          meta: { requiresAuth: true },
        },
        {
          path: "cadre-authorizations",
          name: "cadre-authorizations",
          component: SystemAdminView,
          meta: { requiresAuth: true },
        },
        {
          path: "villager-identities",
          name: "villager-identities",
          component: VillagerDataView,
          meta: { requiresAuth: true },
        },
        {
          path: "villager-ledger-center",
          name: "villager-ledger-center",
          component: VillagerDataView,
          meta: { requiresAuth: true },
        },
        {
          path: "audit-logs",
          name: "audit-logs",
          component: SystemAdminView,
          meta: { requiresAuth: true },
        },
      ],
    },
  ],
});

ensureAuthGuard(router);

export default router;
