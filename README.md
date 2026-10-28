# GDOG 工程手记

把日常开发里的小问题，写成能照着做的笔记。

[阅读网站](https://testgeigei.github.io/engineering-notes/) · [工具箱](https://testgeigei.github.io/engineering-notes/tools/) · [RSS 订阅](https://testgeigei.github.io/engineering-notes/feed.xml) · [纠错与选题](https://github.com/testgeigei/engineering-notes/issues)

## 从一个问题开始

| 你遇到的问题 | 对应笔记 |
| --- | --- |
| Git 改错了，怎么撤回？ | [先分清工作区、暂存区和提交](https://testgeigei.github.io/engineering-notes/notes/git-undo-without-panic/) |
| 已经推送的提交怎么回退？ | [用 revert 保留协作历史](https://testgeigei.github.io/engineering-notes/notes/git-revert-shared-history/) |
| 浏览器为什么拿到旧内容？ | [HTTP 缓存的两个问题](https://testgeigei.github.io/engineering-notes/notes/http-cache-two-questions/) |
| Python 依赖互相冲突？ | [给项目建立虚拟环境](https://testgeigei.github.io/engineering-notes/notes/python-venv-project-boundaries/) |
| SQL 查询慢，从哪里看？ | [从 SQLite 查询计划开始](https://testgeigei.github.io/engineering-notes/notes/sqlite-query-plan-first-step/) |

完整目录包括 Git、HTTP、Python、JSON、URL、SQLite 和排错方法。每篇提供场景、示例和一手文档链接。

## 打开就能用

[浏览器工具箱](https://testgeigei.github.io/engineering-notes/tools/) 提供 JSON 格式化与检查、Unix 时间戳转换、URL 参数拆解、SHA-256 文本摘要。输入只在浏览器处理，无需注册，无第三方脚本。

## 订阅与参与

使用 RSS 阅读器订阅更新；在 GitHub Watch 中选择适合自己的通知。发现错误时请提交 Issue，附上最小示例并移除敏感信息。喜欢某篇笔记，可以直接分享它的固定链接。

AI 辅助资料整理与初稿生成，发布前核对来源、例子与重复内容。编辑规则见 [CONTENT_POLICY.md](CONTENT_POLICY.md)，贡献方式见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 自己运行

仅需 Python 3.11 或以上，无第三方依赖。

```sh
python3 -m unittest -v
python3 site.py build
python3 -m http.server 8000 --bind 127.0.0.1 --directory dist
```

文章源在 `articles.json`，资料目录在 `resources.json`。构建生成静态 HTML、RSS、sitemap、搜索索引和结构化数据。GitHub Actions 在检查通过后部署 `main` 到 Pages；Pull Request 只检查，不部署。

程序 MIT，原创文章 CC BY 4.0；详见 [LICENSE](LICENSE)。
