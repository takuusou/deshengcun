# 得胜村上线冲刺并行清单

## A. 我已经直接完成的

1. 后端 V1 已收口为正式主线：
   - 微信登录
   - 微信 `getPhoneNumber`
   - 基础实名登记（姓名 + 身份证号）
   - 不接 FaceID
   - 不接短信验证码
2. 后端已重新打包并成功部署。
3. 管理后台登录已验证成功。
4. Web 后台最新部署包已重新生成：
   [web_admin_dist_20260401_v1_clean.zip](<PROJECT_ROOT>/web_admin_dist_20260401_v1_clean.zip)
5. 域名切换脚本已准备好：
   [switch_to_custom_domain.py](<PROJECT_ROOT>/scripts/switch_to_custom_domain.py)
6. 户籍白名单导入模板已准备好：
   [villager_roster_template.csv](<PROJECT_ROOT>/materials/villager_roster_template.csv)
7. 微信提审文案模板已准备好：
   [wechat_review_submission.md](<PROJECT_ROOT>/materials/wechat_review_submission.md)

## B. 你今天必须并行推进的

1. 填写并导入正式户籍白名单。
2. 把 Web 后台部署到正式静态站点。
3. 用微信开发者工具导入最新小程序代码并真机回归。
4. 把提审文案、截图、隐私说明整理好。
5. 修改后台管理员密码。

## C. 域名审核通过后立刻执行

1. 完成 `example.invalid` 注册。
2. 完成备案。
3. 在 CloudBase / 静态站点绑定：
   - `api.example.invalid`
   - `admin.example.invalid`
4. 执行：

```bash
cd <PROJECT_ROOT>
python3 scripts/switch_to_custom_domain.py example.invalid
```

5. 重新部署后端。
6. 重新部署 Web 后台。
7. 在微信公众平台更新合法域名。
8. 重新上传小程序并提审。

## D. 户籍白名单文件要求

1. 文件格式可用 `csv` 或 `xlsx`。
2. 最少要有这两列：
   - `姓名`
   - `身份证号`
3. 可选列：
   - `组别`
4. 导入时会覆盖当前在用名单。

## E. 当前正式域名规划

1. API：`https://api.example.invalid`
2. Web 后台：`https://admin.example.invalid`
