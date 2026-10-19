# Exodus 3 存档修改器

Windows 本地 GUI 工具，当前版本 **v1.3**。导入现有 `EX3Data.SC2Bank` 后编辑、预览并导出，或通过“备份并修改”保存。

## 下载和运行

[下载 v1.3 Windows 发行包](https://github.com/Jokerealm/Exodus3/releases/tag/v1.3)。解压后双击 `Exodus3BankEditor.exe`，无需安装 Python或联网。

## 功能

- 公司勋章、信用点、凭证、神器碎片及三种样本集中编辑。
- 编辑最多15种资源，新增test版的柚矿（Uranium，沿用地图显示名称）、铪矿和钼矿，并同步相应编码和汇总校验。
- 装备仅保留“一键满级”：已有装备设为20级，威望、改造点数、属性和解锁状态保持原值。
- 42款人物皮肤：2款默认免费，另外40款支持单项或全部解锁、穿戴选择与语音静音。
- 修改预览、自动暂存草稿、导出、备份和过期原文件保护。

枪皮及头顶、脚下光环有额外地图名单检查，人物皮肤勾选不会自动放行。详见[皮肤解锁说明](docs/皮肤解锁说明.md)。

## 使用提示

**修改存档是对作者工作的不敬，仅供体验，请在24小时内放弃修改。**

在关闭地图后保存。自动暂存只保存编辑器草稿；原文件备份保存在目标目录的 `EX3-editor-backups` 中。完整操作见[使用说明](docs/使用说明.md)。

12项存档默认保持原样；勾选“编辑 test 新增矿物”后可补齐3项。已有15项的存档会自动载入全部矿物。当前test地图单人局保存时只写前12项，多人局才写15项；新增矿物需要在多人局验证。详见[test矿物解析与验证](docs/test矿物支持.md)。

## 从源码运行

在 Windows 64位安装 Python 3.12，执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

构建独立程序：

```powershell
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

结果位于 `dist/Exodus3BankEditor.exe`。保留 `.spec` 中的 Windows ICU 过滤逻辑，避免从其他软件路径收集不兼容的 DLL。地图使用专用加解密变体，不能直接替换为标准AES库。

## 验证

已通过2499项核心检查、1737个原始数字密文块往返验证、24组历史勋章样本、147个配套整数字段核对、22项皮肤检查，以及18项 v1.2 专项检查。独立程序已启动并渲染界面。详见[验证结果](docs/验证结果.json)。

本次测试没有改动原游戏存档。新生成数值和皮肤尚未经过游戏内验收；地图更新可能改变存储格式。

v1.3 另外通过12项自动化测试，覆盖旧存档无修改导出、三种新矿物、范围与汇总校验、未知字段保留，以及GUI预览、重置、旧/新草稿恢复和备份导出。运行：`python -m unittest discover -s tests -v`。这些测试使用合成存档，不读写游戏存档；新增矿物尚未在游戏内验收。

## 项目文件

| 文件 | 用途 |
| --- | --- |
| `app.py` | Qt界面、草稿和文件操作 |
| `bank_model.py` | 存档解析、字段修改、校验和备份 |
| `sc2_cipher.py`、`cipher_tables.py` | 地图专用加解密 |
| `skin_catalog.py` | 人物皮肤名称与免费索引 |
| `Exodus3BankEditor.spec`、`build.ps1` | Windows程序构建 |
| `third-party-licenses/` | 第三方组件许可证 |

界面参照 Bank Generator。背景来源于[StarCraft2-Bank-Restorer 的 bg2.jpg](https://github.com/DarthVan/StarCraft2-Bank-Restorer/blob/bin/assets/images/backgrounds/bg2.jpg)，组件许可证见 `third-party-licenses/`。
