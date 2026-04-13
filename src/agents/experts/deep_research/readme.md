
# 说明

以并行方式根据任务进行文本搜索

任务 -> query生成 -> 搜索 -> 提取有效信息 -> 分析总结


deep_research_agent: 
query_agent: 从 current_parameter 中读取 task_query，生成query_list 写入到 current_output 和 deep_research/query_list
search_worker_agent: worker i 从 deep_research/query_list 读取第i个query，执行搜索，搜索结果写入 deep_research/search_output_i
extract_worker_agent: worker i 从 deep_research/search_output_i 读取搜索结果，提取总结相关信息，写入到 deep_research/extract_result_i
report_agent: 读取所有 deep_research/extract_result_i 信息，生成分析报告，写入 current_output


# TODO
 - 暂时只用此路径下的代码，可能和上一层的有重复。后续考虑合并或者删除。
 - 图像分析和检索

# 参考
- https://github.com/SkyworkAI/DeepResearchAgent


bug: 会出现后面subagent没有等到前面搜索完成就结束的问题。