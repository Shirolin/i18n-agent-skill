# 隐私盾 (Privacy Guard) 脱敏机制

在执行国际化提取和翻译同步任务时，安全性是首要考量。`i18n-agent-skill` 集成了高强度的隐私脱敏机制，确保敏感信息不会泄漏到 LLM 翻译后端。

## 核心脱敏逻辑

 privacy_guard 会在数据离开本地环境前执行以下扫描：

1. **凭证扫描 (Credential Scanning)**:
   - 匹配常见的 API Keys (OpenAI, AWS, GitHub 等)。
   - 匹配数据库连接字符串 (Data Source Names)。
   - 匹配硬编码的密码和令牌。

2. **PII 识别 (Personally Identifiable Information)**:
   - 识别并脱敏邮件地址。
   - 识别并脱敏手机号码。
   - 识别并脱敏内部私有 IP 地址。

3. **路径敏感度**:
   - 自动移除本地绝对路径，仅保留相对于项目根目录的相对路径。

## 脱敏处理方式

- **哈希化**: 关键标识符将被替换为不可逆的哈希值，保持上下文引用的连贯性。
- **占位符化**: 敏感信息替换为特定的占位符（如 `[SENSITIVE_EMAIL]`, `[API_KEY]`）。

## 合规提示
当 `telemetry` 探测到可能的隐私风险时，系统会强制中断流程并要求用户进行 `Status` 确认。严禁绕过此逻辑。
