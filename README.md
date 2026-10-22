# 得胜服务通 · v1.1.0

面向村民的公益服务微信小程序，配套村干部管理后台。项目希望让村务信息更容易获取，让便民办事和处理结果更容易查询，不以盈利为目的。

项目案例文章：[得胜服务通 · Notion 项目介绍](https://wide-nest-95c.notion.site/3f715452b84481a9a9a7f9bfb8e40a9f)。

村民端（小程序）
 <img width="1454" height="768" alt="8d65657d-8507-4d32-a6bc-7d541703392f" src="https://github.com/user-attachments/assets/260b34b8-0fca-467a-bd13-d2d79045a52e" />
<img width="1458" height="764" alt="2e4dbf40-eb80-4ed7-8cc4-0a40679df3e4" src="https://github.com/user-attachments/assets/70122895-51a5-4af5-bd14-6ace13adfbc3" />

村委端（管理端）
<img width="3826" height="1694" alt="ef6f0219-afad-4158-84e2-e9a7bc1fed73" src="https://github.com/user-attachments/assets/0d6eab8d-de0b-4a95-b837-39a0792e84c2" />
<img width="2048" height="989" alt="image" src="https://github.com/user-attachments/assets/18229fe2-45f3-4baa-bee8-11778ad750cb" />
<img width="2048" height="988" alt="image" src="https://github.com/user-attachments/assets/d969d135-10e1-48c7-b83a-53972e936ad3" />

本仓库保存 **v1.1.0 网安整改版本的脱敏求职展示代码**。这里没有生产数据库、户籍名册、真实环境配置或原项目 Git 历史；联系人、联系电话及部署标识已替换为示例或配置占位内容。展示仓库从干净的初始提交开始，不是可直接覆盖生产的部署包。

真实村委会印章图片未上传，原印章资源位置使用项目图标占位。

## 功能

- 信息展示：通知、村务公开、便民服务介绍、村内好物。
- 村民服务：微信登录、手机号绑定、实名匹配、诉求和建议、办件申请、培训与志愿活动报名、个人办理记录。
- 管理后台：内容维护、办件处理、村民台账、干部授权、账号管理及审计日志。
- 通知详情不再提供村民评论、回执或干部回复；通知内容可无需登录查看。

村民提交的业务材料和个人办理记录不作为公开评论展示给其他村民。

## 技术栈与结构

| 部分 | 技术 | 目录 |
| --- | --- | --- |
| 微信小程序 | 原生 JavaScript / WXML / WXSS | `miniprogram/` |
| 管理后台 | Vue 3 / Vite / Pinia / Vue Router | `web-admin/` |
| 后端 | Python / FastAPI / Uvicorn | `backend/` |
| 数据与存储 | MySQL、私有对象存储 | 部署时独立配置 |

`backend/sql/mysql_schema.sql` 是表结构定义，`backend/scripts/` 包含维护工具，`docs/` 包含安全运行资料。维护脚本需人工审阅后使用，克隆仓库不会自动执行脚本或连接数据库。

## 本版本的安全整改

- 删除通知回执、评论和对应接口及建表定义。
- 身份证与手机号查询从无盐 SHA-256 改为独立根密钥、独立用途域的 HMAC-SHA-256。
- 敏感字段使用加密存储，管理端按业务规则脱敏展示。
- 身份证展示保留前六位，其余隐藏；手机号展示保留前三位与后四位。
- 保留生产环境安全校验、后台口令要求及 MFA 机制。
- 户籍重建工具与数据清理方案不在克隆时执行；仓库不包含实际重建数据。

以上描述的是代码机制，不构成“绝无漏洞”或已通过外部测评的声明。

## 开发与配置

后端依赖见 `backend/requirements.txt`，管理后台依赖见 `web-admin/package.json`。配置模板位于 `backend/.env.example` 和 `web-admin/.env.example`。

开始本地开发前，请独立准备开发数据库与开发配置，填入符合现有安全校验要求的密钥。不要使用生产数据库，也不要通过放宽校验让缺失配置通过。小程序 AppID、云托管环境、API 地址和服务联系电话需按自己的环境配置。

```bash
# 在仓库根目录操作；以下步骤仅安装依赖，不启动服务。
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cd ../web-admin
npm ci
```

小程序使用微信开发者工具打开 `miniprogram/`。后台与后端的运行、发布流程见各目录说明；脱敏占位值必须先完成配置。

## 项目状态与展示

当前处于持续完善阶段。面试展示将逐步补充经核实的个人贡献、设计取舍、脱敏界面截图和验证记录，不使用真实村民材料或生产凭证作为示例。

测试身份使用以 `00` 开头的虚构行政区划，保留生日、性别位与校验位测试；测试电话使用 `100`、`101` 开头的虚构号码，仅用于本地格式处理和脱敏断言。它们不代表真实居民身份证或村民手机号。测试口令仅用于临时测试数据，不是生产凭证。原来的 `run_local.sh` 含硬编码演示口令，不随展示仓库提供。

微信订阅通知模板 ID 不提供真实默认值，需通过 `WECHAT_NOTICE_SUBSCRIBE_TEMPLATE_ID` 自行配置；未配置时沿用现有的“订阅不可用”分支。图片的非必要 EXIF/XMP/文字元数据已移除，图像内容保持不变。提交身份使用 GitHub noreply 邮箱。

## 数据与凭证边界

不得提交 `.env`、密钥、Token、连接串、户籍名册、数据库、备份或村民材料。公开前复核完整提交历史与图片内容；后续每次更新也须遵守这一边界。

尚未选择开源许可证。后续公开展示与许可安排将另行确定。
