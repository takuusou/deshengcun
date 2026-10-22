# 得胜村便民服务 CloudBase 部署说明

## 1. 目标形态
- 小程序 JSON 接口通过 `wx.cloud.callContainer` 调后端容器。
- 生产主身份来自 CloudBase 注入的 `x-wx-openid` / `x-wx-unionid`。
- 后端运行在微信云托管容器中。
- 数据库使用托管 MySQL 8.0。
- 附件使用私有对象存储，业务库继续保存平台内部访问路径，访问时临时签名。
- 仅保留图片访问所需的最小公网入口。

## 2. 目录与文件
- 容器镜像定义：`backend/Dockerfile`
- 运行依赖：`backend/requirements.txt`
- 环境变量模板：`backend/.env.example`
- MySQL 建表：`backend/sql/mysql_schema.sql`
- SQLite 迁移脚本：`backend/scripts/migrate_sqlite_to_mysql.py`
- 上传迁移脚本：`backend/scripts/migrate_local_uploads.py`

## 3. 云托管配置
- 服务名建议使用：`deshengcun-api`
- 监听端口：`80`
- 启动命令：镜像默认 `uvicorn app.main:app --host 0.0.0.0 --port 80`
- 建议开启容器鉴权，并在小程序里使用 `wx.cloud.callContainer`
- 若绝大多数接口只给小程序访问，可关闭普通业务公网访问，仅保留图片访问域名

## 4. 环境变量
- 把 `backend/.env.example` 复制为 `backend/.env`
- 至少补齐：
- `CLOUDBASE_ENV_ID`
- `CLOUDBASE_SERVICE_NAME`
- `PUBLIC_API_BASE_URL`
- `WECHAT_MINI_APP_ID`
- `WECHAT_MINI_APP_SECRET`
- `DESHENGCUN_DATABASE_URL`
- `OBJECT_STORAGE_*`
- `UPLOAD_URL_SIGN_SECRET`
- `ID_CARD_AES_KEY_HEX`
- `PHONE_AES_KEY_HEX`

## 5. 数据库初始化
- 在目标 MySQL 里执行 `backend/sql/mysql_schema.sql`
- 或首次启动时让应用自动执行建表
- 旧 SQLite 迁移：
- `python scripts/migrate_sqlite_to_mysql.py --sqlite backend/data/deshengcun_v1.db --mysql-url "$DESHENGCUN_DATABASE_URL" --truncate`
- 校验：
- `python scripts/verify_mysql_migration.py --sqlite backend/data/deshengcun_v1.db --mysql-url "$DESHENGCUN_DATABASE_URL"`

## 6. 附件迁移
- 先把对象存储环境变量配好
- 运行：
- `python scripts/migrate_local_uploads.py --source-dir backend/uploads`
- 迁移后，`/api/v1/uploads/access/...` 会优先从对象存储取临时授权地址；历史本地文件仍保留兼容读取

## 7. 小程序配置
- `miniprogram/config/cloudbase.js`
- 填入：
- `enabled: true`
- `envId`
- `service`
- `publicBaseUrl`
- `miniprogram/config/release.js`
- 本地开发仍可继续填本地 API 地址；生产调用优先走 `callContainer`

## 8. 上线顺序建议
- 先部署容器到测试环境并开启容器鉴权
- 再接 MySQL 测试库
- 再接私有对象存储
- 通过真机回归后，再迁正式 SQLite 数据
- 最后迁历史附件并切正式 `PUBLIC_API_BASE_URL`
