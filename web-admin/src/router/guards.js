import { useAuthStore } from "../stores/auth";

export function ensureAuthGuard(router) {
  router.beforeEach(async (to) => {
    const authStore = useAuthStore();
    if (authStore.token && !authStore.user && !authStore.loadingProfile) {
      try {
        await authStore.fetchMe();
      } catch (err) {
        authStore.clearSession();
      }
    }
    if (to.meta?.requiresAuth && !authStore.isAuthenticated) {
      return {
        name: "login",
        query: { redirect: to.fullPath || "/" },
      };
    }
    const needsSecuritySetup = Boolean(
      authStore.user?.password_reset_required || authStore.user?.mfa_setup_required
    );
    if (authStore.isAuthenticated && needsSecuritySetup && to.name !== "security-setup") {
      return { name: "security-setup" };
    }
    if (authStore.isAuthenticated && !needsSecuritySetup && to.name === "security-setup") {
      return { name: "dashboard" };
    }
    if (to.meta?.public && authStore.isAuthenticated) {
      return { name: "dashboard" };
    }
    return true;
  });
}
