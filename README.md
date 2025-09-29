# GIWA Bridge Test Tool

一个用于 **GIWA ↔ Ethereum Sepolia** 的自动化测试工具，覆盖 ETH 与 ERC-20 代币双向桥接、批量分发、合约部署、多账户循环压测等典型场景。适合个人开发者自测、生态项目 PoC、以及团队联调验证。

> **仅限测试网使用！** 请勿导入主网私钥或用于真实资产。

---

## ✨ 你能用它做什么

* **Sepolia ETH → GIWA ETH**（L1→L2）
* **GIWA ETH → Sepolia ETH**（L2→L1，MessagePasser 方法 A，需后续 prove/finalize）
* **Sepolia ERC-20 ↔ GIWA ERC-20**（含余额检测与水龙头 `claimFaucet` 尝试）
* **批量分发 + 桥接**（从第 1 个地址向其余地址发放 0.1 ETH，并自动桥接一半到 GIWA）
* **GIWA L2 合约多样化部署**（Minimal / Storage / ERC20 / ERC721 / ERC1155 / Timelock / MultiSig）
* **多账户随机一键全流程**（可切换 24 小时循环无人值守）

---

## 🧱 仓库结构

```
giwa-bot/
├─ README.md            # 本说明
├─ add.txt              # 你的测试网私钥清单（手动创建）
├─ requirements.txt     # Python 依赖
└─ bot.py  # 主程序（你当前使用的整合版脚本）
```

---

## ⚡ 5 分钟快速上手

### 第 1 步：获取代码 & 安装依赖

```bash
# 克隆你的仓库
git clone https://github.com/optimus-a1/giwa-bot.git
cd giwa-bot

# 安装 Python 依赖（任选其一）
pip install -r requirements.txt


> 依赖建议 Python 3.10+；若要部署合约模块，脚本会自动安装 `solc 0.8.20`（使用 `py-solc-x`）。

### 第 2 步：准备私钥（仅测试网）

创建 `add.txt`：

```bash
# 方式一：手动创建
nano add.txt

# 方式二：一次写入示例（请改成自己的）
cat > add.txt << 'EOF'
# 第一个私钥作为源账户（分发/桥接的资金来源）
0x你的测试网私钥1

# 以下每行一个接收账户（批量测试目标）
0x你的测试网私钥2
0x你的测试网私钥3
EOF
```

> **安全提醒**：
>
> * 仅使用**测试网**私钥！
> * 不要把私钥提交到任何公共仓库或泄露给他人。

### 第 3 步：准备测试 ETH / 代币

* **Sepolia ETH 水龙头**：

  * [https://faucets.chain.link/sepolia](https://faucets.chain.link/sepolia)
  * [https://www.alchemy.com/faucets/ethereum-sepolia](https://www.alchemy.com/faucets/ethereum-sepolia)


  * Sepolia ETH挖水： https://sepolia-faucet.pk910.de/
  * giwa ETH挖水：https://faucet.giwa.io/


    

* **ERC-20 测试代币**：

  * 脚本会在桥接前检查余额；若代币合约支持 `claimFaucet()`，会自动尝试领取。
  * 也可以通过菜单 **[2] 领取测试代币** 主动领取。

> 建议每个账户 **≥ 0.05 Sepolia ETH**，确保能支付测试与桥接 Gas。

### 第 4 步：运行

```bash
python3 bot.py
```

看到如下菜单即代表启动成功：

```
🌉 GIWA ↔ Sepolia 跨链桥接自动化测试工具 v2.0

╔══════════════════════════════════════════════════════════════════╗
║                          🌉 GIWA 测试菜单                        ║
╠══════════════════════════════════════════════════════════════════╣
║ [1] 🎯 批量分发+桥接      │ 从首个账户分发0.1ETH并桥接0.05ETH   ║
║ [2] 🪙 领取测试代币        │ 从 L1/L2 水龙头领取 ERC-20 测试代币  ║
║ [3] 🪙 ERC-20桥接(L1→L2)  │ Sepolia → Giwa ERC-20               ║
║ [4] 💰 ETH桥接(L2→L1)     │ Giwa ETH → Sepolia ETH（MessagePasser║
║ [5] 🔄 ERC-20桥接(L2→L1)  │ Giwa ERC-20 → Sepolia ERC-20        ║
║ [6] 🔁 L2 ETH自转测试      │ GIWA 内自转 0.00005 ETH             ║
║ [7] 🚀 智能合约部署        │ GIWA 多合约连续部署诊断             ║
║ [8] 🎲 多账户循环测试      │ 随机顺序，可选 24 小时无人值守       ║
║ [0] 🚪 退出程序            │                                     ║
╚══════════════════════════════════════════════════════════════════╝
```

---

## 🔧 可配置项（环境变量）

脚本已内置默认 RPC，可按需覆盖（可选）：

```bash
# L1：Ethereum Sepolia
export L1_RPC="https://ethereum-sepolia-rpc.publicnode.com"

# L2：GIWA Sepolia
export L2_RPC="https://sepolia-rpc.giwa.io"
```

---

## 🧭 推荐测试路径

**第一次使用**

1. 选择 **[2] 领取测试代币**（若代币支持 `claimFaucet`）
2. 选择 **[3] Sepolia ERC-20 → Giwa ERC-20**
3. 选择 **[4] Giwa ETH → Sepolia ETH**（初始化提现，后续需在 L1 证明/最终化）

**团队联调**

1. 选择 **[1] 批量分发+桥接**（快速准备多地址资金）
2. 视需要执行 **[3]~[7]**
3. 选择 **[8] 多账户循环测试** 做回归/压力与可用性验证（可 24h 无人值守）

---

## 🧩 关键信息（与你程序一致）

* **默认 RPC**

  * L1（Sepolia）：`https://ethereum-sepolia-rpc.publicnode.com`
  * L2（GIWA）：`https://sepolia-rpc.giwa.io`

* **合约地址**

  * L1 Standard Bridge：`0x77b2ffc0F57598cAe1DB76cb398059cF5d10A7E7`
  * L2 Standard Bridge：`0x4200000000000000000000000000000000000010`
  * L2 MessagePasser：  `0x4200000000000000000000000000000000000016`
  * L1 ERC-20：`0x50B1eF6e0fe05a32F3E63F02f3c0151BD9004C7c`
  * L2 ERC-20：`0xB11E5c9070a57C0c33Df102436C440a2c73a4c38`

* **区块浏览器**

  * L1：[https://sepolia.etherscan.io/](https://sepolia.etherscan.io/)
  * L2：[https://sepolia-explorer.giwa.io/](https://sepolia-explorer.giwa.io/)

* **默认金额（可在脚本顶部常量修改）**

  * 批量分发每地址：`0.1 ETH`（其中 **50%** 立刻桥接到 L2）
  * L1→L2 ETH：`0.0002 ETH`
  * L2→L1 ETH：`0.0001 ETH`（MessagePasser 方法 A）
  * ERC-20 桥接：`10 * 10^18`（10 枚，18 位小数）

---

## 🧪 菜单对照表

| 选项      | 功能                                    | 适合场景               |
| ------- | ------------------------------------- | ------------------ |
| **[1]** | 批量分发 + 桥接                             | 多人测试前准备资金          |
| **[2]** | 领取测试代币（L1/L2/批量）                      | ERC-20 用例前置补给      |
| **[3]** | Sepolia ERC-20 → Giwa ERC-20          | 上行桥接验证             |
| **[4]** | Giwa ETH → Sepolia ETH（MessagePasser） | 下行提取初始化（后续 7 天挑战期） |
| **[5]** | Giwa ERC-20 → Sepolia ERC-20          | 代币向下提现初始化          |
| **[6]** | Giwa ETH 自转                           | L2 连通性 / 费用 / 出块体验 |
| **[7]** | Giwa 多合约部署测试                          | 编译/部署/Nonce/费率诊断   |
| **[8]** | 多账户随机一键全流程（可 24h 循环）                  | 回归/稳定性/长时观测        |

> **关于提现（L2→L1）**：这是 OP Stack/Bedrock 语义，初始化后需要在 L1 完成 prove & finalize，**全流程约 7 天**。脚本已按规范完成 L2 侧初始化（MessagePasser 方法 A）。

---

## 🧠 常见问题与快速排查

* **`replacement transaction underpriced`**
  说明手续费过低。脚本自带 **提速（speed-up）** 逻辑，会自动上调 `maxPriorityFeePerGas / maxFeePerGas` 重发。

* **`execution reverted`（L2→L1 提现）**
  若直接调 L2 Standard Bridge 失败，请改用 **[4] MessagePasser 方法 A**（脚本已默认采用该方法）。
  初始化成功后，需等待挑战期并在 L1 执行 prove/finalize。

* **`insufficient funds for gas * price + value`**
  余额不足以覆盖 **value + 最大 gas 费**。脚本会提示当前余额与最坏成本，按提示补充余额或调小金额。

* **`Transaction not found` / L2 入账未见变动**
  L1→L2 是 **异步** 处理，通常 **数分钟** 才能在 L2 看到余额变化（与索引/批处理有关）。脚本内置 `等待 L2 入账` 辅助提示。

* **合约部署失败 / `solc` 找不到**
  首次运行合约部署模块会自动安装 `solc 0.8.20`。若网络不通导致失败，请手动重试或先离线安装代理。

---

## 🧰 进阶使用

### 无人值守（24 小时循环）

```bash
screen -S giwa_bot
python3 bot.py
# 菜单选 [8] → 按提示选择 24h 循环
# Ctrl + A + D 断开会话（不杀进程）
```



### 自定义金额 / 手续费策略

编辑 `giwa_bridge_test.py` 顶部**常量区**（`AMOUNT_ETH_PER_TARGET`、`BRIDGE_FRACTION`、`DEPOSIT_ETH_AMOUNT`、`WITHDRAW_ETH_AMOUNT`、`ERC20_AMOUNT` 等）。
手续费在 `fee_profile()` 与 `get_eip1559_fees()` 中集中处理，不建议大改。

---

## 🔒 安全与合规

* 仅在测试网使用；不要导入主网私钥。
* 不要把 `add.txt` 上传到公共仓库。
* 任何桥接/提现逻辑都以 **官方合约 + 公链语义** 为准，脚本仅为自动化工具。

---

## 📎 参考链接

* **Sepolia Explorer**：[https://sepolia.etherscan.io/](https://sepolia.etherscan.io/)
* **GIWA Explorer**：[https://sepolia-explorer.giwa.io/](https://sepolia-explorer.giwa.io/)

---

## 🐞 反馈与支持

* Issue：[https://github.com/optimus-a1/giwa-bot/issues](https://github.com/optimus-a1/giwa-bot/issues)
* 说明文档：本 README 即最新版使用说明

---

**现在就开始你的 GIWA 跨链测试之旅吧！** 🚀
建议从 **[2] 领取测试代币** 与 **[3] L1→L2 ERC-20 桥接** 开始，熟悉流程后再尝试 **[8] 多账户循环测试**。
