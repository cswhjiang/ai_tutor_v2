
## Executor 的输入
current_plan，即如下的结构
```json
{
  "next_agent": "AgentName", 
  "parameters": {
    "param1_for_agent": "value1"
  },
  "summary": "对你当前决策的简短总结，会展示给用户。"
}
```

## Executor 的输出
current_output，即如下的结构
```json
{ "author": 'AgentName', // 必填。输出信息的agent名字。必选
  "status": 'success', // 必填。调用是否成功
  "message": message,  // 必填。调用结果的总结，如果调用出错，这里是错误信息。如果调用成功，这里是成功信息的总结。一般都很短。
  "output_text": output_text, // 必填。agent 回复中的全部文本信息，可以为空字符串。
  "output_artifacts": [binary_result], //可选。agent 返回的二进制文件列表。
} 
```


## Executor 的执行流程：

1. 确定是否需要重新生成next action，如果是则生成

2. 构造参数，包含检查agent是否存在，检查 artifact （规定以 `input_name` 命名）， 将当前的参数写入state `current_parameters` 中。

3. 运行expert，agent 自己将运行的结果写到 `state['current_output']`中

4. 更新 artifacts_history 、text_history、message_history、summary_history，把新生成的artifact保存到本地
然后通过 event 将所有信息保存到session中