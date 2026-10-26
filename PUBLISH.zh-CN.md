# 发布步骤（中文逐步版）

> 每一步都写了**页面上英文按钮的原文**，照着找就行。
> 卡在哪一步就告诉我，不用勉强。

---

## 第 1 步：建一个空仓库

打开 → **https://github.com/new**

页面上有几个框，按下面填：

| 页面上的英文 | 中文意思 | 你要做的 |
|---|---|---|
| **Repository name** | 仓库名字 | 填 `anchor` |
| **Description** | 描述（可不填） | 空着 |
| **Public / Private** | 公开 / 私有 | 选 **Public**（公开）|
| **Add a README file** | 添加说明文件 | **不要勾** |
| **Add .gitignore** | 添加忽略文件 | **不要勾** |
| **Choose a license** | 选择许可证 | **不要勾** |

然后点最下面的绿色按钮 **Create repository**（创建仓库）。

> ⚠️ 那三个勾千万不要勾。我们本地已经有这些文件了，勾了会冲突。

做完这一步，你会看到一个空仓库页面，上面有一堆命令提示——**不用管它**。

---

## 第 2 步：配 SSH 公钥（推荐，不需要任何密码）

> **为什么不用令牌**：令牌是一串能直接推代码的密码，贴进聊天记录或写进文件就泄露了
> （本项目真发生过一次）。公钥可以随便公开，私钥永远不出你的电脑。

### 2.1 生成密钥对

PowerShell 里跑：

```powershell
ssh-keygen -t ed25519 -N '""' -C "anchor@$(hostname)" -f $env:USERPROFILE\.ssh\id_ed25519
```

会生成两个文件：

```
id_ed25519        ← 私钥，不要外发，不要提交
id_ed25519.pub    ← 公钥，可以公开
```

### 2.2 把公钥加到 GitHub

```powershell
Get-Content $env:USERPROFILE\.ssh\id_ed25519.pub
```

复制输出那一整行（`ssh-ed25519 AAAA... `），然后：

**github.com → 右上头像 → Settings → 左侧「SSH and GPG keys」→ New SSH key**

| 字段 | 填什么 |
|---|---|
| Title | `anchor-win`（随便起） |
| Key type | 认证密钥 / Authentication Key |
| Key | 粘那一整行公钥 |

点 **Add SSH key**。

### 2.3 22 端口被挡的话，走 443

国内网络常常连不上 github.com 的 22 端口，报：

```
ssh: connect to host github.com port 22: Connection refused
```

GitHub 官方支持 SSH over 443。在 `C:\Users\<你>\.ssh\config` 里写：

```
Host github.com
  HostName ssh.github.com
  Port 443
  User git
  StrictHostKeyChecking accept-new
```

**这条配一次就够**，以后 `git push` 自动走 443。

### 2.4 验证连通

```powershell
ssh -T git@github.com
```

看到这句就成了（**退出码是 1，这是正常的**，GitHub 不给 shell 权限）：

```
Hi <你的用户名>! You've successfully authenticated, but GitHub does not provide shell access.
```

---

## 第 2 步（备选）：生成令牌（Token）

> 只有在 SSH 实在用不了时才走这条。**令牌等于密码，用完立刻删。**

打开 → **https://github.com/settings/tokens**

1. 点右上 **Generate new token** → 选 **Generate new token (classic)**
2. 可能要你输一次密码确认
3. 页面上填：
   - **Note**（备注）：填 `anchor-push`
   - **Expiration**（有效期）：选 `7 days`（七天，够了）
   - **Select scopes**（权限范围）：**只勾最上面的 `repo`**（它下面的子项会自动全勾）
4. 拉到最底，点绿色按钮 **Generate token**
5. 页面会显示一串 `ghp_xxxxxxxx...` —— **这就是令牌**

> 🔴 **这串东西只显示一次**，关掉页面就再也看不到了。
> 先复制到一个记事本里放着，用完可以删掉。

---

## 第 3 步：把代码推上去

### 走 SSH（推荐）

```powershell
cd F:\llm
```

```powershell
git remote add origin git@github.com:Suhanyv/anchor.git
```

```powershell
git push -u origin main --tags
```

**没有弹窗，不问密码。** 直接开始推。

### 走令牌（备选）

```powershell
git remote add origin https://github.com/Suhanyv/anchor.git
```

```powershell
git push -u origin main --tags
```

弹出窗口问你要账号密码：

| 它问什么 | 你填什么 |
|---|---|
| **Username**（用户名）| `Suhanyv` |
| **Password**（密码）| **粘第 2 步那串 `ghp_...` 令牌** |

> 🔴 **这里填令牌，不是你的账号密码。**
> 输的时候屏幕可能不显示任何字（这是正常的，不是卡住），粘完直接回车。

---

### 推之前先自检这三项

```powershell
# 1. 有没有把令牌/私钥漏进提交
git log --all --oneline -S 'ghp_' --pickaxe-regex
git log --all --oneline -S 'github_pat_' --pickaxe-regex

# 2. 有没有把环境/模型/缓存提交进去（应该一个都没有）
git ls-files | Select-String '^(python312|\.venv|models|cache)/'

# 3. 能不能快进（不能的话说明远端历史和你本地不一样，先别推）
git merge-base --is-ancestor origin/main HEAD
```

**三项都过了再推。** 第一项有输出说明泄露过，要先把那条历史清掉。

### 推成功长这样

```
   80dab08..d229f2a  main -> main
 * [new tag]         v0.1.9 -> v0.1.9
```

**看到这两行就成了。** 刷新一下你的仓库页面，文件都在。

---

## 第 4 步：做发布页（Release）

1. 打开你的仓库页面，右边找 **Releases**，点它
2. 点 **Create a new release**（或 **Draft a new release**）
3. 填：
   - **Choose a tag**：点下拉，选 `v0.1.0`
   - **Release title**：粘这个 → `v0.1.0 研究预览 · research preview`
   - **Describe this release**：把 `RELEASE_v0.1.0.zh.md` 里的内容**整段粘进来**
4. **不要上传任何文件**（Attach binaries 那里空着）
5. 拉到最底，点 **Publish release**

---

## 完成之后

告诉我一声。我会从公网重新下载一次你的仓库，验证：
- 文件齐不齐
- 别人 clone 下来能不能跑通
- 有没有遗漏

---

## 如果卡住了

常见情况：

| 现象 | 原因 | 怎么办 |
|---|---|---|
| `remote origin already exists` | 之前配过 | 先跑 `git remote remove origin` 再重来 |
| 弹窗反复要密码 | 令牌贴错了 | 重新复制令牌，注意不要多空格 |
| `repository not found` | 仓库名不对 | 确认是 `anchor`，不是 `anchor.git` 打错 |
| `src refspec main does not match` | 分支名不对 | 跑 `git branch` 看是不是 `master` |
| 完全没有弹窗，直接报错 | 凭据管理器有问题 | 告诉我错误原文，我来改配置 |

**任何一步看不懂，把那行英文发给我，我用中文告诉你在说什么。**
