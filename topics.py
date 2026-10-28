"""Stable topic routes shared by publishing and change notifications."""
import hashlib

TOPICS = {
    'Git 与协作': ('git', '先看清改动，再处理历史。按工作区、暂存区、共享提交的顺序阅读，最后把协作入口写进 README。'),
    'Web 基础': ('web', '从请求和响应理解浏览器行为。先读缓存，再沿状态码缩小排错范围，用 URL 工具检查实际参数。'),
    '命令行与脚本': ('command-line', '让脚本的输入与运行环境可重复。先隔离 Python 依赖，再用最小 JSON 输入定位数据问题。'),
    '数据与配置': ('data', '先取得执行证据，再改变配置。以 SQLite 查询计划为起点，观察数据规模、筛选条件与索引的关系。'),
    '工程方法': ('practice', '把问题写成可重现、可检查的小步骤。从最小复现开始，记录预期、实际结果和影响范围。'),
}

def topic_slug(category):
    # New categories remain stable until an editor supplies a human-readable route.
    return TOPICS[category][0] if category in TOPICS else 'topic-' + hashlib.sha256(category.encode()).hexdigest()[:12]

def topic_description(category):
    return TOPICS.get(category, ('', '围绕同一类问题整理笔记，先理解场景，再运行例子，最后查阅一手资料。'))[1]
