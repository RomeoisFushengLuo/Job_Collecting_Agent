# 求职信息聚合 Agent

每周二、周四自动搜集美国 / 新加坡 / 香港的职位信息，汇总后发邮件给你。

## 数据来源

| 来源 | 接入方式 | 覆盖地区 |
|---|---|---|
| Greenhouse | 官方公开API，直连 | 你在 `config/companies.yaml` 里配置的公司 |
| MyCareersFuture | 公开接口，直连 | 新加坡 |
| LinkedIn / Indeed / Glassdoor / Handshake / JobsDB | 解析你邮箱收到的 Job Alert 订阅邮件 | 取决于你在各网站设置的订阅条件 |

## 部署步骤

### 1. 新建一个GitHub仓库，把这些文件传上去

把这个文件夹的内容推到你的GitHub仓库（私有仓库即可，不需要公开）。

### 2. 准备两个邮箱

- **专用订阅邮箱**（建议新开一个，比如 Gmail）：用来接收 LinkedIn / Indeed / Glassdoor / Handshake / JobsDB 的 Job Alert 邮件，保持干净、方便程序用 IMAP 读取。去这5个网站分别设置职位订阅（建议频率选"每日"），发到这个邮箱。
- **发信邮箱**：用来发送汇总邮件，可以和上面的专用邮箱是同一个，也可以用你日常邮箱。

Gmail 用户注意：需要先在 [Google账号安全设置](https://myaccount.google.com/security) 里开启"两步验证"，然后生成一个"应用专用密码"（App Password），IMAP/SMTP都要用这个专用密码，不能用你的常规登录密码。

### 3. 在GitHub仓库里配置Secrets

进入仓库 `Settings > Secrets and variables > Actions`，点 "New repository secret"，逐个添加：

```
SMTP_HOST        smtp.gmail.com
SMTP_PORT        587
SMTP_USER        你的发信邮箱
SMTP_PASSWORD    发信邮箱的应用专用密码
RECIPIENT_EMAIL  你想接收汇总邮件的地址

IMAP_HOST        imap.gmail.com
IMAP_PORT        993
IMAP_USER        你的专用订阅邮箱
IMAP_PASSWORD    专用订阅邮箱的应用专用密码
```

### 4. 编辑配置文件

- `config/keywords.yaml`：按国家/地区配置关键词和排除词
- `config/companies.yaml`：填入你想追踪的、用Greenhouse招聘系统的公司清单

改完直接在GitHub网页上编辑提交，或者本地改完 `git push`，下次运行自动生效。

### 5. 手动测试一次

去仓库的 `Actions` 标签页，选择 "Job Search Agent" 工作流，点击右侧 "Run workflow" 手动触发一次，检查日志和收到的邮件是否符合预期。

### 6. 之后就是全自动的了

`.github/workflows/job_search.yml` 里配置了每周二、四自动运行（UTC 15:00，约等于太平洋时间早上7-8点，具体见workflow文件里的注释）。运行完成后会自动把去重记录更新提交回仓库，不需要你手动干预。

## 已知限制 / 后续优化方向
 
1. **邮件解析器还需要用真实样本校准**：`sources/email_parsers/` 下5个解析器目前是基于通用HTML结构写的启发式规则，还没有用真实邮件测试调准过。建议你运行一段时间后，把解析效果不好的邮件转发给我，针对性修正对应网站的parser。
2. **Greenhouse只能覆盖你指定的公司**：不是全网搜索，需要你在 `companies.yaml` 里持续补充公司清单。
3. **MyCareersFuture用的是非官方接口**：目前工作正常，但新加坡政府随时可能调整接口，如果某天突然报错，需要重新抓包核实新的接口地址。
4. **邮件订阅来源的地区分类是猜测性的**：`main.py` 里的 `classify_email_job_by_region` 函数目前靠职位地点/关键词简单判断属于哪个地区，猜不出来的默认归为US，可以后续优化得更精确。

## 本地测试

```bash
pip install -r requirements.txt

# 单独测试某个数据源
python sources/api/greenhouse_source.py
python sources/api/mycareersfuture_source.py

# 完整跑一遍主流程（需要先配置好环境变量，见 .env.example）
python main.py
```
