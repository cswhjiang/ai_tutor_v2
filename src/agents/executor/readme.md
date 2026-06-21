
## Runtime 的输出协议

当前 `AgentInvocationService` 不再执行 plan，也不再直接调用 expert runner。它负责两件事：

1. 将 ADK Runner 的流式事件转换成前端使用的 SSE event。
2. 将 expert 写入 `state.current_output` 的结果持久化到 artifact history 和本地输出目录。

`current_output` 结构如下：
```json
{ "author": 'AgentName', // 必填。输出信息的agent名字。必选
  "status": 'success', // 必填。调用是否成功
  "message": message,  // 必填。调用结果的总结，如果调用出错，这里是错误信息。如果调用成功，这里是成功信息的总结。一般都很短。
  "output_text": output_text, // 必填。agent 回复中的全部文本信息，可以为空字符串。
  "output_artifacts": [binary_result], //可选。agent 返回的二进制文件列表。
} 
```
