<template>
  <section ref="root" class="ad-page-shell">
    <section class="dashboard-hero-card">
      <div class="dashboard-hero-bg"></div>
      <div class="dashboard-hero-body">
        <div>
          <div class="dashboard-hero-kicker">ADMIN DASHBOARD</div>
          <div class="dashboard-hero-title">得胜村便民服务后台</div>
          <div class="dashboard-hero-sub">集中处理诉求、办件、通知、志愿活动、公开信息和授权管理。</div>
        </div>
        <div class="dashboard-hero-side">
          <div class="dashboard-hero-side-label">当前登录</div>
          <div class="dashboard-hero-side-name">{{ authStore.user?.display_name || authStore.user?.real_name || "-" }}</div>
          <div class="dashboard-hero-side-role">{{ roleLabel }}</div>
        </div>
      </div>
    </section>

    <div v-if="dashboardError" class="inline-error">{{ dashboardError }}</div>

    <section class="ad-stats">
      <article v-for="item in statCards" :key="item.label" class="ad-sc" :data-n="item.watermark">
        <div class="ad-sc-l">{{ item.label }}</div>
        <div class="ad-sc-n" :style="{ color: item.color || 'var(--color-kincha)' }">
          {{ item.value }}
          <span class="ad-sc-u">{{ item.unit }}</span>
        </div>
        <div class="ad-sc-t" :class="item.tone">{{ item.hint }}</div>
      </article>
    </section>

    <section class="ad-grid-2">
      <article class="ad-card">
        <div class="ad-card-head">
          <span class="ad-card-title">待处理事项</span>
          <span class="ad-card-sub">需要今日跟进</span>
        </div>
        <div class="ad-todo">
          <RouterLink class="ad-ti" to="/requests">
            <div class="ad-ti-dot"></div>
            <div class="ad-ti-body">
              <div class="ad-ti-title">诉求与办件待处理</div>
              <div class="ad-ti-meta">集中查看诉求、政务办件和办理进度。</div>
            </div>
            <div class="ad-ti-time">{{ pendingTotal }} 件</div>
            <div class="ad-ti-arr" aria-hidden="true">
              <svg viewBox="0 0 24 24"><polyline points="9,18 15,12 9,6" /></svg>
            </div>
          </RouterLink>
          <RouterLink class="ad-ti" to="/notices">
            <div class="ad-ti-dot"></div>
            <div class="ad-ti-body">
              <div class="ad-ti-title">发布管理</div>
              <div class="ad-ti-meta">通知、志愿活动统一在这里维护。</div>
            </div>
            <div class="ad-ti-time">进入</div>
            <div class="ad-ti-arr" aria-hidden="true">
              <svg viewBox="0 0 24 24"><polyline points="9,18 15,12 9,6" /></svg>
            </div>
          </RouterLink>
          <RouterLink class="ad-ti" to="/villager-identities">
            <div class="ad-ti-dot"></div>
            <div class="ad-ti-body">
              <div class="ad-ti-title">村民数据</div>
              <div class="ad-ti-meta">实名信息和台账查询集中到一个分组中处理。</div>
            </div>
            <div class="ad-ti-time">进入</div>
            <div class="ad-ti-arr" aria-hidden="true">
              <svg viewBox="0 0 24 24"><polyline points="9,18 15,12 9,6" /></svg>
            </div>
          </RouterLink>
        </div>
      </article>

      <article class="ad-card">
        <div class="ad-card-head">
          <span class="ad-card-title">最近操作</span>
          <span class="ad-card-sub">今日后台动作</span>
        </div>
        <div v-if="loadingLogs" class="ad-empty">正在加载最近日志...</div>
        <div v-else-if="!recentLogs.length" class="ad-empty">最近还没有可展示的日志。</div>
        <div v-else class="ad-log">
          <div v-for="item in recentLogs" :key="item.id" class="ad-li">
            <div class="ad-li-head">
              <span class="ad-li-act">{{ translateAuditAction(item.action) }}</span>
              <span class="ad-li-t">{{ formatNiceTime(item.created_at) }}</span>
            </div>
            <div class="ad-li-meta">{{ item.actor_display_name || "系统记录" }} · {{ item.target_type || "-" }}</div>
            <div class="ad-li-code">{{ item.target_type || "-" }} / {{ item.target_id || "-" }}</div>
          </div>
        </div>
      </article>
    </section>
  </section>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { gsap } from "gsap";

import { listAdminAuditLogs } from "../../api/audit";
import { fetchAdminNavBadges } from "../../api/nav-badges";
import { listAdminMetrics } from "../../api/open";
import { useAuthStore } from "../../stores/auth";
import { extractApiError } from "../../utils/admin-ui";
import { translateAuditAction } from "../../utils/audit";
import { formatNiceTime } from "../../utils/time";

const authStore = useAuthStore();
const root = ref(null);
let mm;
const pendingCounts = ref({
  requests: 0,
  govApplications: 0,
});
const metricCount = ref(0);
const recentLogs = ref([]);
const loadingLogs = ref(false);
const dashboardError = ref("");

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

const pendingTotal = computed(() => pendingCounts.value.requests + pendingCounts.value.govApplications);
const statCards = computed(() => [
  {
    label: "待处理诉求",
    value: pendingCounts.value.requests,
    unit: "件",
    hint: "当前待处理数量",
    tone: "",
    watermark: String(pendingCounts.value.requests || 0),
  },
  {
    label: "待办政务件",
    value: pendingCounts.value.govApplications,
    unit: "件",
    hint: "正常处理中",
    tone: "",
    watermark: String(pendingCounts.value.govApplications || 0),
  },
  {
    label: "公开指标",
    value: metricCount.value,
    unit: "项",
    hint: "公开页指标数量",
    tone: "",
    watermark: String(metricCount.value || 0),
  },
  {
    label: "近期日志",
    value: recentLogs.value.length,
    unit: "条",
    hint: "工作台展示最近 6 条",
    tone: "",
    watermark: String(recentLogs.value.length || 0),
  },
]);

async function loadDashboard() {
  if (!authStore.token) {
    return;
  }
  loadingLogs.value = true;
  dashboardError.value = "";
  try {
    const [navBadges, metrics, logs] = await Promise.all([
      fetchAdminNavBadges(authStore.token),
      listAdminMetrics(authStore.token),
      listAdminAuditLogs(authStore.token, { limit: 6 }),
    ]);
    pendingCounts.value = {
      requests: Number(navBadges?.requests || 0),
      govApplications: Number(navBadges?.gov_applications || 0),
    };
    metricCount.value = Array.isArray(metrics) ? metrics.length : 0;
    recentLogs.value = Array.isArray(logs) ? logs.slice(0, 6) : [];
  } catch (error) {
    dashboardError.value = extractApiError(error, "工作台数据加载失败，请稍后重试。");
  } finally {
    loadingLogs.value = false;
  }
}

function playEntrance() {
  if (!root.value) return;
  mm = gsap.matchMedia();
  mm.add(
    {
      reduceMotion: "(prefers-reduced-motion: reduce)",
      normalMotion: "(prefers-reduced-motion: no-preference)",
    },
    (ctx) => {
      const heroLines = [".dashboard-hero-kicker", ".dashboard-hero-title", ".dashboard-hero-sub"];
      const heroSide = ".dashboard-hero-side > *";
      const content = [".ad-sc", ".ad-grid-2 > .ad-card"];

      // 用户偏好减弱动效：直接呈现，不做位移/淡入
      if (ctx.conditions.reduceMotion) {
        gsap.set([...heroLines, heroSide, ...content], { autoAlpha: 1, clearProps: "all" });
        return;
      }

      const tl = gsap.timeline({ defaults: { ease: "power3.out" } });

      // 标题逐行淡入上移
      tl.from(heroLines, {
        autoAlpha: 0,
        y: 26,
        duration: 0.7,
        stagger: 0.12,
      });
      tl.from(
        heroSide,
        {
          autoAlpha: 0,
          y: 16,
          duration: 0.5,
          stagger: 0.08,
        },
        "-=0.45"
      );

      // 内容缓慢弹出
      tl.from(
        ".ad-sc",
        {
          autoAlpha: 0,
          y: 28,
          scale: 0.96,
          duration: 0.7,
          stagger: 0.1,
          ease: "back.out(1.5)",
        },
        "-=0.2"
      );
      tl.from(
        ".ad-grid-2 > .ad-card",
        {
          autoAlpha: 0,
          y: 32,
          scale: 0.97,
          duration: 0.75,
          stagger: 0.14,
          ease: "back.out(1.4)",
        },
        "-=0.45"
      );
    },
    root.value
  );
}

onMounted(() => {
  loadDashboard();
  playEntrance();
});

onUnmounted(() => {
  mm?.revert();
});
</script>

<style scoped>
.ad-page-shell {
  gap: 16px;
}

.dashboard-hero-card {
  position: relative;
  overflow: hidden;
  border-radius: 12px;
  background: linear-gradient(135deg, #a63d2f 0%, #c04535 100%);
  box-shadow: 0 20px 40px rgba(166, 61, 47, 0.18);
}

.dashboard-hero-bg {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse at 80% 50%, rgba(255, 255, 255, 0.1) 0%, transparent 60%),
    radial-gradient(ellipse at 10% 80%, rgba(0, 0, 0, 0.15) 0%, transparent 50%);
}

.dashboard-hero-body {
  position: relative;
  z-index: 1;
  padding: 24px 28px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  color: #fff;
}

.dashboard-hero-kicker {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.7);
  letter-spacing: 0.28em;
  margin-bottom: 7px;
  font-family: var(--font-serif);
}

.dashboard-hero-title {
  font-family: var(--font-serif);
  font-size: 24px;
  color: #fff;
  font-weight: 500;
  letter-spacing: 0.16em;
  margin-bottom: 5px;
}

.dashboard-hero-sub {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.75);
  letter-spacing: 0.03em;
}

.dashboard-hero-side {
  text-align: right;
}

.dashboard-hero-side-label {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.6);
  letter-spacing: 0.16em;
  margin-bottom: 5px;
}

.dashboard-hero-side-name {
  font-family: var(--font-serif);
  font-size: 18px;
  color: #fff;
  letter-spacing: 0.12em;
  font-weight: 500;
}

.dashboard-hero-side-role {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.65);
  margin-top: 3px;
}

@media (max-width: 960px) {
  .dashboard-hero-body {
    flex-direction: column;
    align-items: flex-start;
  }

  .dashboard-hero-side {
    text-align: left;
  }
}

@media (max-width: 640px) {
  .dashboard-hero-card {
    border-radius: 10px;
  }

  .dashboard-hero-body {
    padding: 20px 18px;
    gap: 14px;
  }

  .dashboard-hero-title {
    font-size: 21px;
    line-height: 1.35;
    letter-spacing: 0.08em;
  }

  .dashboard-hero-sub {
    line-height: 1.65;
  }
}
</style>
