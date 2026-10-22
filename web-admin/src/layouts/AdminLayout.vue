<template>
  <div class="office-layout" :class="{ 'mobile-nav-open': isMobileNavOpen }">
    <div v-if="isMobileViewport && isMobileNavOpen" class="office-backdrop" @click="closeMobileNav"></div>

    <header class="office-topbar">
      <div class="office-topbar-left">
        <button
          v-if="isMobileViewport"
          class="office-menu-btn"
          type="button"
          :aria-expanded="isMobileNavOpen"
          aria-label="打开后台导航"
          @click="toggleMobileNav"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M4 7h16M4 12h16M4 17h16" />
          </svg>
        </button>
        <div class="office-topbar-brand">
          <img class="office-topbar-seal" :src="sealSrc" alt="得胜村委会印章" />
          <div>
            <div class="office-topbar-brand-name">得胜村委会</div>
            <div class="office-topbar-brand-sub">后台管理系统</div>
          </div>
        </div>
      </div>

      <div class="office-topbar-center">
        <div v-if="isMobileViewport" class="office-mobile-brand" aria-label="得胜服务通">
          <img :src="sealSrc" alt="" />
          <span>得胜服务通</span>
        </div>
        <div v-else class="office-breadcrumb">
          <span>{{ currentGroupTitle }}</span>
          <span class="office-breadcrumb-divider">·</span>
          <span class="office-breadcrumb-current">{{ currentPageLabel }}</span>
        </div>
      </div>

      <div class="office-topbar-right" aria-hidden="true"></div>
    </header>

    <div class="office-body">
      <aside class="office-sidebar" :class="{ 'mobile-open': isMobileNavOpen }">
      <div class="office-brand">
        <div>
          <div class="office-brand-kicker">后台导航</div>
          <div class="office-brand-title">村务协同</div>
        </div>
      </div>

      <nav class="office-nav">
        <div v-for="group in navGroups" :key="group.title" class="office-nav-group">
          <div class="office-nav-group-title">{{ group.title }}</div>
          <RouterLink
            v-for="item in group.items"
            :key="item.to"
            class="office-nav-link"
            :class="{ active: isNavActive(item) }"
            :to="item.to"
            @click="handleNavClick"
          >
            <span class="office-nav-main">
              <span class="office-nav-icon" v-html="item.iconSvg"></span>
              <span>{{ item.label }}</span>
            </span>
            <span v-if="navBadgeCount(item) > 0" class="office-nav-badge">{{ navBadgeText(navBadgeCount(item)) }}</span>
          </RouterLink>
        </div>
      </nav>

      <div class="office-sidebar-account">
        <div class="office-user-avatar" aria-hidden="true">
          <svg viewBox="0 0 24 24">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
            <circle cx="12" cy="7" r="4" />
          </svg>
        </div>
        <div class="office-user">
          <div class="office-user-name">{{ authStore.user?.display_name || authStore.user?.real_name || "未登录" }}</div>
          <div class="office-user-role">{{ roleLabel }}</div>
        </div>
        <button class="ghost-btn office-logout-btn" type="button" @click="handleLogout">退出</button>
      </div>
      </aside>

      <div class="office-main">
      <main class="office-content">
        <RouterView />
      </main>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { RouterLink, RouterView, useRoute, useRouter } from "vue-router";

import { fetchAdminNavBadges } from "../api/nav-badges";
import sealSrc from "../assets/deshengcun-logo.png";
import { useAuthStore } from "../stores/auth";

const authStore = useAuthStore();
const route = useRoute();
const router = useRouter();
const isMobileViewport = ref(false);
const isMobileNavOpen = ref(false);
const navBadgeCounts = ref({
  requests: 0,
  gov_applications: 0,
});
let navBadgeTimer = 0;

const navIcons = {
  dashboard:
    '<svg viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>',
  tasks:
    '<svg viewBox="0 0 24 24"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>',
  publish:
    '<svg viewBox="0 0 24 24"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>',
  open:
    '<svg viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/></svg>',
  villagers:
    '<svg viewBox="0 0 24 24"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/></svg>',
  system:
    '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06A1.65 1.65 0 0 0 15 19.4a1.65 1.65 0 0 0-1 .6V21a2 2 0 0 1-4 0v-1a1.65 1.65 0 0 0-1-.6 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.6 15a1.65 1.65 0 0 0-.6-1H3a2 2 0 0 1 0-4h1a1.65 1.65 0 0 0 .6-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.6a1.65 1.65 0 0 0 1-.6V3a2 2 0 0 1 4 0v1a1.65 1.65 0 0 0 1 .6 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9c.14.35.35.66.6 1h1a2 2 0 0 1 0 4h-1a1.65 1.65 0 0 0-.6 1z"/></svg>',
};

const navGroups = [
  {
    title: "核心",
    items: [
      { to: "/", label: "工作台", iconSvg: navIcons.dashboard, names: ["dashboard"] },
      { to: "/notices", label: "发布管理", iconSvg: navIcons.publish, names: ["notices", "training-programs", "volunteer-events", "open"] },
      { to: "/requests", label: "事务办理", iconSvg: navIcons.tasks, names: ["requests", "gov-applications"] },
    ],
  },
  {
    title: "数据",
    items: [
      // 隐藏-待恢复：数字公开并入发布管理，原 /open 路由与页面保留。
      { to: "/villager-identities", label: "村民数据", iconSvg: navIcons.villagers, names: ["villager-identities", "villager-ledger-center"] },
    ],
  },
  {
    title: "系统",
    items: [{ to: "/cadre-authorizations", label: "系统管理", iconSvg: navIcons.system, names: ["cadre-authorizations", "audit-logs"] }],
  },
];

const allNavItems = computed(() => navGroups.flatMap((group) => group.items.map((item) => ({ ...item, groupTitle: group.title }))));

const roleLabel = computed(() => {
  const value = String(authStore.user?.role_key || "").trim();
  const officeTitle = String(authStore.user?.office_title || "").trim();
  let permissionLabel = "";
  if (value === "super_admin") {
    permissionLabel = "超级管理员";
  } else if (value === "cadre") {
    permissionLabel = "普通干部";
  } else if (value === "readonly") {
    permissionLabel = "只读协办";
  } else {
    permissionLabel = value || "未设置角色";
  }
  return officeTitle ? `${permissionLabel} / ${officeTitle}` : permissionLabel;
});

const currentNavItem = computed(() => {
  const currentName = String(route.name || "").trim();
  return allNavItems.value.find((item) => item.names.includes(currentName)) || allNavItems.value[0];
});

const currentPageLabel = computed(() => currentNavItem.value?.label || "后台管理");
const currentGroupTitle = computed(() => currentNavItem.value?.groupTitle || "核心");

function isNavActive(item) {
  const currentName = String(route.name || "").trim();
  return item.names.includes(currentName);
}

function syncViewportState() {
  isMobileViewport.value = window.innerWidth <= 1080;
  if (!isMobileViewport.value) {
    isMobileNavOpen.value = false;
  }
}

function toggleMobileNav() {
  if (!isMobileViewport.value) {
    return;
  }
  isMobileNavOpen.value = !isMobileNavOpen.value;
}

function closeMobileNav() {
  isMobileNavOpen.value = false;
}

function handleNavClick() {
  closeMobileNav();
}

function navBadgeCount(item) {
  const names = item?.names || [];
  if (names.includes("requests") || names.includes("gov-applications")) {
    return Number(navBadgeCounts.value.requests || 0) + Number(navBadgeCounts.value.gov_applications || 0);
  }
  return 0;
}

function navBadgeText(value) {
  const count = Number(value || 0);
  if (count > 99) {
    return "99+";
  }
  return String(Math.max(0, count));
}

async function refreshNavBadges() {
  if (!authStore.token) {
    navBadgeCounts.value = {
      requests: 0,
      gov_applications: 0,
    };
    return;
  }
  try {
    const result = await fetchAdminNavBadges(authStore.token);
    navBadgeCounts.value = {
      requests: Number(result?.requests || 0),
      gov_applications: Number(result?.gov_applications || 0),
    };
  } catch (error) {
    // Keep navigation responsive even when badge refresh fails.
  }
}

function handleWindowFocus() {
  refreshNavBadges();
}

function handleNavBadgeRefresh() {
  refreshNavBadges();
}

async function handleLogout() {
  closeMobileNav();
  try {
    await authStore.logout();
  } finally {
    await router.replace({ name: "login" });
  }
}

watch(
  () => route.fullPath,
  () => {
    closeMobileNav();
    refreshNavBadges();
  }
);

watch(isMobileNavOpen, (isOpen) => {
  document.body.classList.toggle("admin-mobile-nav-open", isOpen && isMobileViewport.value);
});

onMounted(() => {
  syncViewportState();
  window.addEventListener("resize", syncViewportState);
  window.addEventListener("focus", handleWindowFocus);
  window.addEventListener("admin-nav-badges:refresh", handleNavBadgeRefresh);
  navBadgeTimer = window.setInterval(refreshNavBadges, 45000);
  refreshNavBadges();
});

onBeforeUnmount(() => {
  document.body.classList.remove("admin-mobile-nav-open");
  window.removeEventListener("resize", syncViewportState);
  window.removeEventListener("focus", handleWindowFocus);
  window.removeEventListener("admin-nav-badges:refresh", handleNavBadgeRefresh);
  if (navBadgeTimer) {
    window.clearInterval(navBadgeTimer);
    navBadgeTimer = 0;
  }
});
</script>

<style scoped>
.office-layout {
  min-height: 100vh;
  min-height: 100dvh;
  display: grid;
  grid-template-rows: 54px minmax(0, 1fr);
  background: var(--color-bg);
}

.office-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(26, 22, 18, 0.22);
  z-index: 39;
}

.office-sidebar {
  height: calc(100vh - 54px);
  padding: 16px 0;
  background: var(--color-sidebar);
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.office-body {
  min-height: 0;
  height: calc(100vh - 54px);
  display: grid;
  grid-template-columns: 200px minmax(0, 1fr);
}

.office-brand {
  padding: 2px 24px 16px;
}

.office-brand-kicker {
  font-size: 9px;
  color: var(--color-text-hint);
  letter-spacing: 0.08em;
}

.office-brand-title {
  margin-top: 2px;
  font-size: 12px;
  line-height: 1.35;
  font-weight: 600;
  color: var(--color-text);
  letter-spacing: 0.08em;
}

.office-nav {
  display: grid;
  gap: 2px;
  flex: 1 1 auto;
  min-height: 0;
  align-content: start;
  overflow-y: auto;
  padding-bottom: 18px;
}

.office-sidebar-account {
  display: grid;
  grid-template-columns: 30px minmax(0, 1fr);
  align-items: center;
  gap: 10px 12px;
  margin: auto 12px 0;
  padding: 12px;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.58);
}

.office-nav-group {
  display: grid;
  gap: 2px;
}

.office-nav-group-title {
  padding: 12px 22px 6px;
  font-size: 9px;
  color: var(--color-text-hint);
  font-weight: 600;
  letter-spacing: 0.28em;
}

.office-nav-link {
  position: relative;
  min-height: 40px;
  margin: 0 10px;
  padding: 0 10px 0 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-radius: 8px;
  color: var(--color-text-sub);
}

.office-nav-link::before {
  content: "";
  position: absolute;
  left: 0;
  top: 10px;
  bottom: 10px;
  width: 2px;
  border-radius: 999px;
  background: transparent;
}

.office-nav-link.active {
  background: var(--color-sidebar-active);
  color: var(--color-primary);
  font-weight: 600;
}

.office-nav-link.active::before {
  background: var(--color-primary);
}

.office-nav-badge {
  min-width: 16px;
  height: 16px;
  padding: 0 5px;
  border-radius: 8px;
  background: var(--color-primary);
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 9px;
}

.office-nav-main {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.office-nav-icon {
  width: 20px;
  height: 20px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border-radius: 6px;
  background: rgba(26, 22, 18, 0.04);
  color: var(--color-text-hint);
  font-size: 11px;
  font-family: var(--font-serif);
}

.office-nav-link.active .office-nav-icon {
  background: var(--color-primary-pale);
  color: var(--color-primary);
}

.office-nav-icon :deep(svg) {
  width: 15px;
  height: 15px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.5;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.office-main {
  min-width: 0;
  min-height: 0;
  overflow: auto;
}

.office-topbar {
  z-index: 20;
  min-height: 54px;
  padding: 0 22px;
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr) 220px;
  align-items: center;
  gap: 18px;
  background: rgba(255, 255, 255, 0.96);
  border-bottom: 1px solid var(--color-border);
  box-shadow: inset 0 -1px 0 rgba(166, 61, 47, 0.08);
}

.office-topbar-left,
.office-topbar-right {
  display: flex;
  align-items: center;
  gap: 14px;
}

.office-topbar-left {
  justify-content: flex-start;
}

.office-topbar-center {
  display: flex;
  justify-content: center;
}

.office-mobile-brand {
  min-width: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-family: var(--font-serif);
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text);
  letter-spacing: 0.08em;
  white-space: nowrap;
}

.office-mobile-brand img {
  width: 26px;
  height: 26px;
  object-fit: contain;
}

.office-topbar-right {
  justify-content: flex-end;
}

.office-menu-btn {
  width: 42px;
  height: 42px;
  padding: 0;
  border-radius: 7px;
  background: #ffffff;
  border: 1px solid var(--color-border);
  color: var(--color-text-sub);
  display: inline-grid;
  place-items: center;
}

.office-menu-btn svg {
  width: 21px;
  height: 21px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
}

.office-topbar-brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.office-topbar-seal {
  width: 34px;
  height: 34px;
  object-fit: contain;
  flex-shrink: 0;
}

.office-topbar-brand-name {
  font-family: var(--font-serif);
  font-size: 14px;
  color: var(--color-text);
  letter-spacing: 0.08em;
}

.office-topbar-brand-sub {
  margin-top: 1px;
  font-size: 9px;
  color: var(--color-text-hint);
  letter-spacing: 0.12em;
}

.office-breadcrumb {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--color-text-hint);
  letter-spacing: 0.04em;
}

.office-breadcrumb-divider {
  opacity: 0.5;
}

.office-breadcrumb-current {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text);
}

.office-user {
  text-align: right;
  min-width: 0;
}

.office-user-avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: var(--color-primary-pale);
  border: 1px solid rgba(166, 61, 47, 0.18);
  color: var(--color-primary);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.office-user-avatar svg {
  width: 14px;
  height: 14px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.5;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.office-user-name {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text);
}

.office-user-role {
  margin-top: 2px;
  font-size: 10px;
  color: var(--color-text-hint);
  overflow-wrap: anywhere;
}

.office-logout-btn {
  min-width: 70px;
  min-height: 34px;
  border-radius: 18px;
}

.office-sidebar-account .office-user {
  text-align: left;
}

.office-sidebar-account .office-user-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.office-sidebar-account .office-logout-btn {
  grid-column: 1 / -1;
  width: 100%;
  min-height: 36px;
  border-radius: 8px;
}

.office-content {
  padding: 24px 28px 32px;
}

@media (max-width: 1080px) {
  .office-layout {
    grid-template-rows: 58px minmax(0, 1fr);
  }

  .office-body {
    height: calc(100vh - 58px);
    grid-template-columns: 1fr;
  }

  .office-sidebar {
    position: fixed;
    inset: 58px auto 0 0;
    width: min(280px, 84vw);
    height: calc(100vh - 58px);
    height: calc(100dvh - 58px);
    z-index: 40;
    transform: translateX(-100%);
    transition: transform 0.18s ease;
  }

  .office-sidebar.mobile-open {
    transform: translateX(0);
  }

  .office-topbar {
    min-height: 58px;
    padding: 0 18px;
    grid-template-columns: 42px minmax(0, 1fr) 42px;
  }

  .office-content {
    padding: 18px;
  }

  .office-topbar-brand {
    display: none;
  }
}

@media (max-width: 640px) {
  .office-topbar {
    padding: 0 12px;
    gap: 10px;
  }

  .office-topbar-center {
    min-width: 0;
    justify-content: center;
  }

  .office-sidebar {
    width: min(320px, 88vw);
    padding-bottom: env(safe-area-inset-bottom);
  }

  .office-sidebar-account {
    margin-bottom: max(8px, env(safe-area-inset-bottom));
  }

  .office-nav-link {
    min-height: 46px;
  }

  .office-content {
    padding: 12px;
  }
}
</style>
