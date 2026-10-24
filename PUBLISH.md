# 发布步骤（v0.1.0）

> 这台机器**没有任何 git 凭证**（无 gh CLI、无 SSH key、无 token），
> 所以最后一步 push 必须由你授权。

---

## 一、先决定发到哪

| 选 | 适合 | 备注 |
|---|---|---|
| **GitHub** | 想被国际社区看到 | 已测可达（HTTP 200）|
| **Gitee** | 国内访问快 | 已测可达 |

两者都通。仓库 19.7 MB，没有大文件，随便发。

---

## 二、创建空仓库

**GitHub**：https://github.com/new
- Repository name 建议：`anchor` 或 `anchor-style-retrieval`
- **不要**勾选 README / .gitignore / LICENSE（本地都有了）
- Public

**Gitee**：https://gitee.com/projects/new
- 同上，不要初始化仓库

---

## 三、配 remote 并推

把 `<URL>` 换成你刚建的仓库地址：

```powershell
cd F:\llm
git remote add origin <URL>
git push -u origin main --tags
```

用 HTTPS 的话，push 时会要你输用户名和 **Personal Access Token**（不是密码）：

- GitHub：Settings → Developer settings → Personal access tokens → 勾 `repo`
- Gitee：设置 → 私人令牌 → 勾 `projects`

> 凭据会由 Windows 凭据管理器（`helper-selector`）记住，只需输一次。

---

## 四、发布页（Release）

推完之后在仓库页面 **Releases → Draft a new release**：

- Tag：`v0.1.0`（已在本地打好，推送时带过去了）
- Title：`v0.1.0 研究预览 · research preview`
- 描述：直接把 `CHANGELOG.md` 里 v0.1.0 那一节粘过去
- **不上传任何文件**（权重刻意不发，见 MODEL_CARD）

---

## 五、发布前最后三件事（我来做，你说一声）

1. **决定 git 作者身份要不要改**
   现在是 `solo-dev <solo@localhost>`。公开仓库里这样显示会有点怪。
   - 保留：无所谓，很多项目都用占位
   - 改：只能改**以后**的提交；改历史的作者需要 rebase，我会先备份

2. **要不要清 git 历史里的两个坏提交**
   中间有 2 个提交把 `bench/interesting_report.json` 写坏过（最终状态是好的）。
   不影响 clone 和使用，只是 `git log` 里看起来像手滑。清历史需 rebase，我会先备份。

3. **README 里的占位链接**
   `https://github.com/<your-account>/anchor` 出现在 README / NOTICE / LICENSE-DATA 里。
   你给我实际的账号名，我一次替换掉。

---

## 六、发布后立刻要做的

```
1. 在一个干净目录 git clone 你自己的仓库，跑一遍 src/smoke_test.py
   —— 这次是从公网 clone，能验证推送完整性
2. 给仓库加 topics：text-retrieval, contrastive-learning, comfyui, prompt-engineering
3. 在 ComfyUI 社区/相关讨论区发帖时，第一句就写"这是 v0.1 预览，评测集只有 20 题"
```

---

## 附：当前仓库状态

```
提交数      57+
跟踪文件    240
体积        19.7 MB（不含权重）
分支        main
标签        v0.1.0
远程        未配置
```
