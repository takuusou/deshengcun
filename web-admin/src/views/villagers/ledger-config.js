export const ledgerAgeRules = {
  seniorAge: 60,
  superSeniorAge: 80,
};

function boolLabel(value) {
  return value ? "是" : "否";
}

function textOrDash(value) {
  const text = String(value ?? "").trim();
  return text || "-";
}

export function ageText(value) {
  return Number.isFinite(value) ? `${value} 岁` : "年龄待补充";
}

export function getCivilAgeBand(record) {
  const age = Number(record?.age);
  if (!Number.isFinite(age)) {
    return "待补充";
  }
  if (age >= ledgerAgeRules.superSeniorAge) {
    return "已满80岁";
  }
  if (age >= ledgerAgeRules.seniorAge) {
    return "已满60岁";
  }
  if (record?.is_turning_60_this_year) {
    return "快满60岁";
  }
  return "60岁以下";
}

export function buildCivilLabels(record) {
  const labels = [];
  if (record?.civil?.is_dibao) labels.push("低保");
  if (record?.civil?.is_tekun) labels.push("特困");
  if (record?.civil?.is_lonely_elder) labels.push("孤寡");
  if (record?.civil?.disability_status) labels.push("残疾");
  if (record?.is_turning_60_this_year) labels.push("今年满60");
  if (Number(record?.age) >= ledgerAgeRules.superSeniorAge) labels.push("高龄");
  return labels.length ? labels.join(" / ") : "普通村民";
}

function buildMedicalLabels(record) {
  const labels = [];
  if (record?.medical?.is_insured) labels.push("已参保");
  if (record?.medical?.is_chronic_patient) labels.push("慢病");
  if (record?.medical?.is_major_relief_target) labels.push("大病救助");
  if (record?.medical?.payment_status === "异常未缴") labels.push("未缴");
  return labels.length ? labels.join(" / ") : "待补录";
}

function buildSocialLabels(record) {
  const labels = [];
  if (record?.social?.pension_insured) labels.push("养老在保");
  if (record?.social?.receiving_benefit) labels.push("已领待遇");
  if (record?.social?.flexible_employment) labels.push("灵活就业");
  if (record?.social?.migrant_worker) labels.push("外出务工");
  if (record?.social?.public_welfare_post) labels.push("公益岗位");
  return labels.length ? labels.join(" / ") : "待补录";
}

function buildAgricultureLabels(record) {
  const labels = [];
  if (record?.agriculture?.is_planter) labels.push("种植");
  if (record?.agriculture?.is_breeder) labels.push("养殖");
  if (record?.agriculture?.coop_member) labels.push("合作社");
  if (record?.agriculture?.disaster_affected) labels.push("受灾");
  return labels.length ? labels.join(" / ") : "待补录";
}

function buildEnvironmentLabels(record) {
  const labels = [];
  if (record?.environment?.sanitation_household) labels.push("责任户");
  if (record?.environment?.toilet_renovated) labels.push("厕改");
  if (record?.environment?.waste_demo_household) labels.push("分类示范");
  if (record?.environment?.has_issue) labels.push("有问题");
  if (record?.environment?.pending_rectification) labels.push("待整改");
  return labels.length ? labels.join(" / ") : "待补录";
}

export const ledgerTabsConfig = [
  { key: "civil", label: "民政" },
  { key: "medical", label: "医保" },
  { key: "agriculture", label: "农业" },
  { key: "social", label: "社保" },
  { key: "environment", label: "环境" },
];

export const ledgerStatsConfig = {
  civil: [
    { key: "total", label: "台账总人数", value: (records) => records.length },
    {
      key: "pre-senior",
      label: "快满60岁",
      value: (records) => records.filter((item) => item.is_turning_60_this_year).length,
    },
    {
      key: "senior",
      label: "已满60岁",
      value: (records) => records.filter((item) => item.is_age_60_plus || Number(item.age) >= ledgerAgeRules.seniorAge).length,
    },
    {
      key: "super-senior",
      label: "已满80岁",
      value: (records) =>
        records.filter((item) => item.is_age_80_plus || Number(item.age) >= ledgerAgeRules.superSeniorAge).length,
    },
    { key: "tekun", label: "特困人员", value: (records) => records.filter((item) => item.civil?.is_tekun).length },
  ],
  medical: [
    { key: "total", label: "台账总人数", value: (records) => records.length },
    { key: "insured", label: "已参保", value: (records) => records.filter((item) => item.medical?.is_insured).length },
    {
      key: "chronic",
      label: "慢病人员",
      value: (records) => records.filter((item) => item.medical?.is_chronic_patient).length,
    },
    {
      key: "relief",
      label: "大病救助对象",
      value: (records) => records.filter((item) => item.medical?.is_major_relief_target).length,
    },
    {
      key: "abnormal",
      label: "异常未缴",
      value: (records) => records.filter((item) => item.medical?.payment_status === "异常未缴").length,
    },
  ],
  agriculture: [
    { key: "total", label: "台账总人数", value: (records) => records.length },
    { key: "planter", label: "种植户", value: (records) => records.filter((item) => item.agriculture?.is_planter).length },
    { key: "breeder", label: "养殖户", value: (records) => records.filter((item) => item.agriculture?.is_breeder).length },
    {
      key: "cooperative",
      label: "合作社成员",
      value: (records) => records.filter((item) => item.agriculture?.coop_member).length,
    },
    {
      key: "disaster",
      label: "受灾农户",
      value: (records) => records.filter((item) => item.agriculture?.disaster_affected).length,
    },
  ],
  social: [
    { key: "total", label: "台账总人数", value: (records) => records.length },
    {
      key: "pension",
      label: "养老在保",
      value: (records) => records.filter((item) => item.social?.pension_insured).length,
    },
    {
      key: "benefit",
      label: "领取待遇",
      value: (records) => records.filter((item) => item.social?.receiving_benefit).length,
    },
    {
      key: "migrant",
      label: "外出务工",
      value: (records) => records.filter((item) => item.social?.migrant_worker).length,
    },
    {
      key: "welfare-post",
      label: "公益岗位",
      value: (records) => records.filter((item) => item.social?.public_welfare_post).length,
    },
  ],
  environment: [
    { key: "total", label: "台账总人数", value: (records) => records.length },
    {
      key: "sanitation",
      label: "保洁责任户",
      value: (records) => records.filter((item) => item.environment?.sanitation_household).length,
    },
    {
      key: "toilet",
      label: "厕所改造",
      value: (records) => records.filter((item) => item.environment?.toilet_renovated).length,
    },
    {
      key: "issues",
      label: "存在卫生问题",
      value: (records) => records.filter((item) => item.environment?.has_issue).length,
    },
    {
      key: "pending",
      label: "待整改",
      value: (records) => records.filter((item) => item.environment?.pending_rectification).length,
    },
  ],
};

export const ledgerFilterConfig = {
  civil: [
    { key: "dibao", label: "低保户", predicate: (record) => !!record.civil?.is_dibao },
    { key: "tekun", label: "特困人员", predicate: (record) => !!record.civil?.is_tekun },
    {
      key: "pre-senior",
      label: "快满60岁",
      predicate: (record) => !!record.is_turning_60_this_year,
    },
    {
      key: "senior",
      label: "已满60岁",
      predicate: (record) => !!record.is_age_60_plus || Number(record.age) >= ledgerAgeRules.seniorAge,
    },
    {
      key: "super-senior",
      label: "已满80岁",
      predicate: (record) => !!record.is_age_80_plus || Number(record.age) >= ledgerAgeRules.superSeniorAge,
    },
    { key: "lonely", label: "孤寡老人", predicate: (record) => !!record.civil?.is_lonely_elder },
    { key: "disabled", label: "残疾人员", predicate: (record) => !!record.civil?.disability_status },
    { key: "temp-help", label: "需临时救助", predicate: (record) => !!record.civil?.needs_temp_help },
  ],
  medical: [
    { key: "insured", label: "是否参保", predicate: (record) => !!record.medical?.is_insured },
    {
      key: "payment-year",
      label: "缴费年度",
      predicate: (record) => Number(record.medical?.payment_year) === 2026,
    },
    { key: "chronic", label: "慢病人员", predicate: (record) => !!record.medical?.is_chronic_patient },
    {
      key: "major-relief",
      label: "大病救助对象",
      predicate: (record) => !!record.medical?.is_major_relief_target,
    },
    {
      key: "payment-abnormal",
      label: "异常未缴",
      predicate: (record) => record.medical?.payment_status === "异常未缴",
    },
    { key: "focus", label: "重点关注对象", predicate: (record) => !!record.medical?.focus_person },
  ],
  agriculture: [
    { key: "planter", label: "是否种植户", predicate: (record) => !!record.agriculture?.is_planter },
    { key: "breeder", label: "是否养殖户", predicate: (record) => !!record.agriculture?.is_breeder },
    { key: "coop", label: "合作社成员", predicate: (record) => !!record.agriculture?.coop_member },
    { key: "machine", label: "有农机", predicate: (record) => !!record.agriculture?.has_agri_machine },
    { key: "disaster", label: "是否受灾", predicate: (record) => !!record.agriculture?.disaster_affected },
  ],
  social: [
    { key: "pension", label: "参加养老保险", predicate: (record) => !!record.social?.pension_insured },
    { key: "benefit", label: "领取待遇", predicate: (record) => !!record.social?.receiving_benefit },
    {
      key: "flexible",
      label: "灵活就业",
      predicate: (record) => !!record.social?.flexible_employment,
    },
    { key: "migrant", label: "外出务工", predicate: (record) => !!record.social?.migrant_worker },
    { key: "unemployed", label: "失业待岗", predicate: (record) => !!record.social?.unemployed },
    { key: "veteran", label: "退役军人", predicate: (record) => !!record.social?.veteran },
    { key: "welfare", label: "公益岗位", predicate: (record) => !!record.social?.public_welfare_post },
  ],
  environment: [
    {
      key: "sanitation",
      label: "保洁责任户",
      predicate: (record) => !!record.environment?.sanitation_household,
    },
    {
      key: "toilet",
      label: "厕所改造",
      predicate: (record) => !!record.environment?.toilet_renovated,
    },
    {
      key: "waste-demo",
      label: "垃圾分类示范户",
      predicate: (record) => !!record.environment?.waste_demo_household,
    },
    {
      key: "issue",
      label: "存在卫生问题",
      predicate: (record) => !!record.environment?.has_issue,
    },
    {
      key: "pending",
      label: "是否待整改",
      predicate: (record) => !!record.environment?.pending_rectification,
    },
  ],
};

export const ledgerColumnsConfig = {
  civil: [
    { key: "real_name", label: "姓名", value: (record) => textOrDash(record.real_name) },
    { key: "gender", label: "性别", value: (record) => textOrDash(record.gender) },
    { key: "age", label: "年龄", value: (record) => ageText(record.age) },
    { key: "group", label: "村组", value: (record) => textOrDash(record.village_group) },
    { key: "phone", label: "联系电话（脱敏）", value: (record) => textOrDash(record.phone_masked) },
    { key: "civil-labels", label: "民政标签", value: (record) => buildCivilLabels(record) },
    { key: "civil-status", label: "当前状态", value: (record) => textOrDash(record.statuses?.civil) },
  ],
  medical: [
    { key: "real_name", label: "姓名", value: (record) => textOrDash(record.real_name) },
    { key: "group", label: "村组", value: (record) => textOrDash(record.village_group) },
    { key: "age", label: "年龄", value: (record) => ageText(record.age) },
    { key: "phone", label: "联系电话（脱敏）", value: (record) => textOrDash(record.phone_masked) },
    { key: "medical-tags", label: "医保标签", value: (record) => buildMedicalLabels(record) },
    { key: "payment", label: "缴费状态", value: (record) => textOrDash(record.medical?.payment_status) },
    { key: "status", label: "当前状态", value: (record) => textOrDash(record.statuses?.medical) },
  ],
  agriculture: [
    { key: "real_name", label: "姓名", value: (record) => textOrDash(record.real_name) },
    { key: "group", label: "村组", value: (record) => textOrDash(record.village_group) },
    { key: "age", label: "年龄", value: (record) => ageText(record.age) },
    { key: "phone", label: "联系电话（脱敏）", value: (record) => textOrDash(record.phone_masked) },
    { key: "agri-tags", label: "农业标签", value: (record) => buildAgricultureLabels(record) },
    { key: "crop", label: "主要作物", value: (record) => textOrDash(record.agriculture?.main_crop) },
    { key: "status", label: "当前状态", value: (record) => textOrDash(record.statuses?.agriculture) },
  ],
  social: [
    { key: "real_name", label: "姓名", value: (record) => textOrDash(record.real_name) },
    { key: "group", label: "村组", value: (record) => textOrDash(record.village_group) },
    { key: "age", label: "年龄", value: (record) => ageText(record.age) },
    { key: "phone", label: "联系电话（脱敏）", value: (record) => textOrDash(record.phone_masked) },
    { key: "social-tags", label: "社保标签", value: (record) => buildSocialLabels(record) },
    { key: "employment", label: "就业状态", value: (record) => textOrDash(record.social?.employment_status) },
    { key: "status", label: "当前状态", value: (record) => textOrDash(record.statuses?.social) },
  ],
  environment: [
    { key: "real_name", label: "姓名", value: (record) => textOrDash(record.real_name) },
    { key: "group", label: "村组", value: (record) => textOrDash(record.village_group) },
    { key: "age", label: "年龄", value: (record) => ageText(record.age) },
    { key: "phone", label: "联系电话（脱敏）", value: (record) => textOrDash(record.phone_masked) },
    { key: "env-tags", label: "环境标签", value: (record) => buildEnvironmentLabels(record) },
    { key: "fix-date", label: "最近整改", value: (record) => textOrDash(record.environment?.last_rectified_at) },
    { key: "status", label: "当前状态", value: (record) => textOrDash(record.statuses?.environment) },
  ],
};

export const ledgerDetailSectionsConfig = {
  civil: [
    {
      key: "basic",
      title: "基础信息",
      fields: [
        { label: "姓名", value: (record) => textOrDash(record.real_name) },
        { label: "性别", value: (record) => textOrDash(record.gender) },
        { label: "年龄", value: (record) => ageText(record.age) },
        { label: "出生日期", value: (record) => textOrDash(record.birth_date) },
        { label: "身份证号（脱敏）", value: (record) => textOrDash(record.id_card_masked) },
        { label: "联系电话（脱敏）", value: (record) => textOrDash(record.phone_masked) },
        { label: "村组", value: (record) => textOrDash(record.village_group) },
        { label: "地址", value: (record) => textOrDash(record.address) },
        { label: "实名状态", value: (record) => textOrDash(record.auth_status) },
      ],
    },
    {
      key: "civil",
      title: "民政信息",
      fields: [
        { label: "是否低保户", value: (record) => boolLabel(record.civil?.is_dibao) },
        { label: "是否特困人员", value: (record) => boolLabel(record.civil?.is_tekun) },
        { label: "是否孤寡老人", value: (record) => boolLabel(record.civil?.is_lonely_elder) },
        { label: "残疾情况", value: (record) => textOrDash(record.civil?.disability_status) },
        {
          label: "是否高龄老人",
          value: (record) => boolLabel(Number(record.age) >= ledgerAgeRules.superSeniorAge),
        },
        { label: "年龄分层", value: (record) => getCivilAgeBand(record) },
        { label: "是否需要临时救助", value: (record) => boolLabel(record.civil?.needs_temp_help) },
        { label: "困难类型", value: (record) => textOrDash(record.civil?.hardship_type) },
        { label: "民政备注", value: (record) => textOrDash(record.civil?.remark) },
      ],
    },
    {
      key: "footprint",
      title: "留痕信息",
      fields: [
        { label: "最后更新时间", value: (record) => textOrDash(record.updated_at) },
        { label: "更新人", value: (record) => textOrDash(record.updated_by) },
        { label: "备注", value: (record) => textOrDash(record.remarks) },
      ],
    },
  ],
  medical: [
    {
      key: "basic",
      title: "基础信息",
      fields: [
        { label: "姓名", value: (record) => textOrDash(record.real_name) },
        { label: "年龄", value: (record) => ageText(record.age) },
        { label: "村组", value: (record) => textOrDash(record.village_group) },
        { label: "联系电话（脱敏）", value: (record) => textOrDash(record.phone_masked) },
      ],
    },
    {
      key: "medical",
      title: "医保信息",
      fields: [
        { label: "是否参保", value: (record) => boolLabel(record.medical?.is_insured) },
        { label: "缴费年度", value: (record) => textOrDash(record.medical?.payment_year) },
        { label: "慢病人员", value: (record) => boolLabel(record.medical?.is_chronic_patient) },
        { label: "大病救助对象", value: (record) => boolLabel(record.medical?.is_major_relief_target) },
        { label: "缴费状态", value: (record) => textOrDash(record.medical?.payment_status) },
        { label: "重点关注对象", value: (record) => boolLabel(record.medical?.focus_person) },
        { label: "医保备注", value: (record) => textOrDash(record.medical?.remark) },
      ],
    },
    {
      key: "footprint",
      title: "留痕信息",
      fields: [
        { label: "最后更新时间", value: (record) => textOrDash(record.updated_at) },
        { label: "更新人", value: (record) => textOrDash(record.updated_by) },
        { label: "备注", value: (record) => textOrDash(record.remarks) },
      ],
    },
  ],
  agriculture: [
    {
      key: "basic",
      title: "基础信息",
      fields: [
        { label: "姓名", value: (record) => textOrDash(record.real_name) },
        { label: "村组", value: (record) => textOrDash(record.village_group) },
        { label: "联系电话（脱敏）", value: (record) => textOrDash(record.phone_masked) },
      ],
    },
    {
      key: "agriculture",
      title: "农业信息",
      fields: [
        { label: "是否种植户", value: (record) => boolLabel(record.agriculture?.is_planter) },
        { label: "是否养殖户", value: (record) => boolLabel(record.agriculture?.is_breeder) },
        { label: "主要作物", value: (record) => textOrDash(record.agriculture?.main_crop) },
        { label: "养殖类型", value: (record) => textOrDash(record.agriculture?.breeding_type) },
        { label: "是否合作社成员", value: (record) => boolLabel(record.agriculture?.coop_member) },
        { label: "是否有农机", value: (record) => boolLabel(record.agriculture?.has_agri_machine) },
        { label: "是否受灾", value: (record) => boolLabel(record.agriculture?.disaster_affected) },
        { label: "农业备注", value: (record) => textOrDash(record.agriculture?.remark) },
      ],
    },
    {
      key: "footprint",
      title: "留痕信息",
      fields: [
        { label: "最后更新时间", value: (record) => textOrDash(record.updated_at) },
        { label: "更新人", value: (record) => textOrDash(record.updated_by) },
        { label: "备注", value: (record) => textOrDash(record.remarks) },
      ],
    },
  ],
  social: [
    {
      key: "basic",
      title: "基础信息",
      fields: [
        { label: "姓名", value: (record) => textOrDash(record.real_name) },
        { label: "年龄", value: (record) => ageText(record.age) },
        { label: "村组", value: (record) => textOrDash(record.village_group) },
        { label: "联系电话（脱敏）", value: (record) => textOrDash(record.phone_masked) },
      ],
    },
    {
      key: "social",
      title: "社保信息",
      fields: [
        { label: "是否参加养老保险", value: (record) => boolLabel(record.social?.pension_insured) },
        { label: "是否领取待遇", value: (record) => boolLabel(record.social?.receiving_benefit) },
        { label: "是否灵活就业", value: (record) => boolLabel(record.social?.flexible_employment) },
        { label: "是否外出务工", value: (record) => boolLabel(record.social?.migrant_worker) },
        { label: "是否失业待岗", value: (record) => boolLabel(record.social?.unemployed) },
        { label: "是否退役军人", value: (record) => boolLabel(record.social?.veteran) },
        { label: "是否公益岗位", value: (record) => boolLabel(record.social?.public_welfare_post) },
        { label: "社保备注", value: (record) => textOrDash(record.social?.remark) },
      ],
    },
    {
      key: "footprint",
      title: "留痕信息",
      fields: [
        { label: "最后更新时间", value: (record) => textOrDash(record.updated_at) },
        { label: "更新人", value: (record) => textOrDash(record.updated_by) },
        { label: "备注", value: (record) => textOrDash(record.remarks) },
      ],
    },
  ],
  environment: [
    {
      key: "basic",
      title: "基础信息",
      fields: [
        { label: "姓名", value: (record) => textOrDash(record.real_name) },
        { label: "村组", value: (record) => textOrDash(record.village_group) },
        { label: "联系电话（脱敏）", value: (record) => textOrDash(record.phone_masked) },
      ],
    },
    {
      key: "environment",
      title: "环境信息",
      fields: [
        { label: "是否保洁责任户", value: (record) => boolLabel(record.environment?.sanitation_household) },
        { label: "是否厕所改造", value: (record) => boolLabel(record.environment?.toilet_renovated) },
        {
          label: "是否垃圾分类示范户",
          value: (record) => boolLabel(record.environment?.waste_demo_household),
        },
        { label: "是否存在卫生问题", value: (record) => boolLabel(record.environment?.has_issue) },
        { label: "是否待整改", value: (record) => boolLabel(record.environment?.pending_rectification) },
        { label: "最近整改时间", value: (record) => textOrDash(record.environment?.last_rectified_at) },
        { label: "环境备注", value: (record) => textOrDash(record.environment?.remark) },
      ],
    },
    {
      key: "footprint",
      title: "留痕信息",
      fields: [
        { label: "最后更新时间", value: (record) => textOrDash(record.updated_at) },
        { label: "更新人", value: (record) => textOrDash(record.updated_by) },
        { label: "备注", value: (record) => textOrDash(record.remarks) },
      ],
    },
  ],
};
