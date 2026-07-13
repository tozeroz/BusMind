# BusMind Postman Collection

本目录是当前项目唯一保留的接口测试集合入口，覆盖后端主要 API。

```text
collections/busmind-service/       目录化接口集合
environments/BusMind Local.environment.yaml
globals/workspace.globals.yaml
```

命名约定：

```text
目录名使用小写 kebab-case，不使用空格。
请求文件名保留可读名称，便于在 Postman / Apifox 中识别。
```

旧的 `tools/postman/BusMind-Service-B.postman_collection.json` 只覆盖早期 Service-B 接口，已经删除。后续维护接口集合时优先更新本目录。
