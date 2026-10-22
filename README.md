# 得胜服务通 · v1.1.0

**已上线，为得胜村 9 个村民小组、538 户、1744 位村民提供服务。**

得胜服务通是一款面向真实村级服务场景的公益微信小程序，配套村干部管理后台，用于通知发布、村务公开、便民办事和办理结果查询，不以盈利为目的。

项目案例文章：[得胜服务通 · Notion 项目介绍](https://wide-nest-95c.notion.site/3f715452b84481a9a9a7f9bfb8e40a9f)。

村民端（小程序）
 <img width="1454" height="768" alt="8d65657d-8507-4d32-a6bc-7d541703392f" src="https://github.com/user-attachments/assets/260b34b8-0fca-467a-bd13-d2d79045a52e" />
<img width="1458" height="764" alt="2e4dbf40-eb80-4ed7-8cc4-0a40679df3e4" src="https://github.com/user-attachments/assets/70122895-51a5-4af5-bd14-6ace13adfbc3" />

村委端（管理端）
<img width="3826" height="1694" alt="ef6f0219-afad-4158-84e2-e9a7bc1fed73" src="https://github.com/user-attachments/assets/0d6eab8d-de0b-4a95-b837-39a0792e84c2" />
<img width="2048" height="989" alt="image" src="https://github.com/user-attachments/assets/18229fe2-45f3-4baa-bee8-11778ad750cb" />
<img width="2048" height="988" alt="image" src="https://github.com/user-attachments/assets/d969d135-10e1-48c7-b83a-53972e936ad3" />

本仓库提供 **v1.1.0 网安整改版本的脱敏展示代码**，生产配置与村民业务数据不随代码公开。

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
