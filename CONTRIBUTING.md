# 一起把笔记写清楚

欢迎通过 Issues 提交纠错、选题和工具问题。请给出文章地址、具体问题、预期结果及一手参考来源。截图和日志需要移除凭据与个人信息。

文章唯一源稿为 articles.json。每篇文章使用稳定 id，包含 title、summary、category、date、updated、body 和 sources。不要改变既有文章 id，不通过修改日期制造新鲜度。

提交前运行：

```sh
python3 site.py check
python3 -m unittest -v
python3 site.py build
```

仅将 dist/ 作为网站产物。不要提交环境文件、凭据、编辑器缓存或私人操作记录。新增代码沿用 MIT，原创文章沿用 CC BY 4.0；引用第三方内容时保留来源和其原许可。
