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

## 第 2 步：生成令牌（Token）

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

在你的电脑上打开 **PowerShell**（开始菜单搜 powershell），然后**一行一行**粘贴下面这些，每行按一次回车：

```powershell
cd F:\llm
```

```powershell
git remote add origin https://github.com/Suhanyv/anchor.git
```

```powershell
git push -u origin main --tags
```

第三行执行后会弹出窗口，问你要账号密码：

| 它问什么 | 你填什么 |
|---|---|
| **Username**（用户名）| `Suhanyv` |
| **Password**（密码）| **粘第 2 步那串 `ghp_...` 令牌** |

> 🔴 **这里填令牌，不是你的账号密码。**
> 输的时候屏幕可能不显示任何字（这是正常的，不是卡住），粘完直接回车。

等它跑完，最后会看到类似：

```
 * [new branch]      main -> main
 * [new tag]         v0.1.0 -> v0.1.0
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
