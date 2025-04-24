import boto3

# 初始化 Bedrock 客户端
bedrock_client = boto3.client(
    service_name='bedrock-runtime',
    region_name='us-east-1',  # 替换为你的区域
)

# 定义模型名称和输入
model_id = "anthropic.claude-v3.7-sonnet"  # Claude 3.7 Sonnet 模型
input_text = "请用中文解释量子力学的基本概念。"

# 调用 Bedrock 模型
response = bedrock_client.invoke_model(
    modelId=model_id,
    body=input_text,
    contentType="text/plain",  # 输入类型
    accept="text/plain"        # 输出类型
)

# 解析响应
output_text = response['body'].read().decode('utf-8')
print("模型响应：", output_text)