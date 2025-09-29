#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🌉 GIWA ↔ Sepolia 自动化测试脚本
================================================
一个功能完整的跨链桥接测试工具，支持：
- ETH 和 ERC-20 代币的双向桥接
- 自动化批量分发和桥接
- 智能合约部署测试
- 随机全流程测试

作者: GIWA Team
版本: v2.0
GitHub: https://github.com/your-username/giwa-bridge-test
================================================
"""

import os
import sys
import time
import random
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple, List

from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_account import Account
from eth_account.signers.local import LocalAccount

# 彩色输出支持
try:
    from colorama import init, Fore, Back, Style
    init()
    COLORS_ENABLED = True
except ImportError:
    # 如果没有 colorama，使用空字符串
    class MockColor:
        RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = RESET = ""
        BRIGHT = DIM = ""
    Fore = Back = Style = MockColor()
    COLORS_ENABLED = False

# solc 支持
try:
    from solcx import compile_source, install_solc, set_solc_version, get_installed_solc_versions
    SOLCX_AVAILABLE = True
except Exception:
    SOLCX_AVAILABLE = False

# ========================
# 🎨 美化输出工具
# ========================

def print_banner():
    """打印启动横幅"""
    banner = f"""
{Fore.CYAN}{'='*80}
{Fore.BLUE}    ██████  ██ ██     ██  █████      ████████ ███████ ███████ ████████ 
   ██       ██ ██     ██ ██   ██        ██    ██      ██         ██    
   ██   ███ ██ ██  █  ██ ███████        ██    █████   ███████    ██    
   ██    ██ ██ ██ ███ ██ ██   ██        ██    ██           ██    ██    
    ██████  ██  ███ ███  ██   ██        ██    ███████ ███████    ██    
{Fore.CYAN}
    🌉 GIWA ↔ Sepolia 跨链桥接自动化测试工具 v2.0
    
    📋 支持功能：
    • ETH 双向桥接 (Sepolia ↔ GIWA)
    • ERC-20 代币桥接
    • 批量分发和桥接
    • 智能合约部署测试
    • 一键随机全流程测试
    
{Fore.YELLOW}    ⚠️  请确保在测试网环境中使用！
{'='*80}{Style.RESET_ALL}
"""
    print(banner)

def print_success(message: str):
    """打印成功信息"""
    print(f"{Fore.GREEN}✅ {message}{Style.RESET_ALL}")

def print_error(message: str):
    """打印错误信息"""
    print(f"{Fore.RED}❌ {message}{Style.RESET_ALL}")

def print_warning(message: str):
    """打印警告信息"""
    print(f"{Fore.YELLOW}⚠️  {message}{Style.RESET_ALL}")

def print_info(message: str):
    """打印信息"""
    print(f"{Fore.BLUE}ℹ️  {message}{Style.RESET_ALL}")

def print_step(step: str, message: str):
    """打印步骤信息"""
    print(f"{Fore.MAGENTA}[{step}]{Style.RESET_ALL} {message}")

def print_section_header(title: str):
    """打印章节标题"""
    print(f"\n{Fore.CYAN}{'='*20} {title} {'='*20}{Style.RESET_ALL}")

def format_eth(wei_amount: int) -> str:
    """格式化 ETH 金额显示"""
    eth = Web3.from_wei(wei_amount, 'ether')
    return f"{Fore.GREEN}{eth:.6f} ETH{Style.RESET_ALL}"

def format_address(address: str) -> str:
    """格式化地址显示"""
    return f"{Fore.YELLOW}{address[:6]}...{address[-4:]}{Style.RESET_ALL}"

def print_progress_bar(current: int, total: int, description: str = ""):
    """打印进度条"""
    percent = int((current / total) * 100)
    bar_length = 30
    filled = int((bar_length * current) / total)
    bar = f"{'█' * filled}{'░' * (bar_length - filled)}"
    print(f"\r{Fore.BLUE}[{bar}] {percent}% {description}{Style.RESET_ALL}", end="", flush=True)
    if current == total:
        print()  # 完成时换行

# ========================
# 配置常量
# ========================

L1_RPC_DEFAULT = os.getenv("L1_RPC", "https://ethereum-sepolia-rpc.publicnode.com")
L2_RPC_DEFAULT = os.getenv("L2_RPC", "https://sepolia-rpc.giwa.io")

ADDR_L1_STANDARD_BRIDGE = Web3.to_checksum_address("0x77b2ffc0F57598cAe1DB76cb398059cF5d10A7E7")
ADDR_L2_STANDARD_BRIDGE = Web3.to_checksum_address("0x4200000000000000000000000000000000000010")
ADDR_L2_MESSAGE_PASSER  = Web3.to_checksum_address("0x4200000000000000000000000000000000000016")

ADDR_L1_ERC20 = Web3.to_checksum_address("0x50B1eF6e0fe05a32F3E63F02f3c0151BD9004C7c")
ADDR_L2_ERC20 = Web3.to_checksum_address("0xB11E5c9070a57C0c33Df102436C440a2c73a4c38")

DEFAULT_L2_GAS_LIMIT_MSG = 200_000
TX_WAIT_TIMEOUT   = 240
TX_POLL_INTERVAL  = 2
REPLACE_BUMP      = 1.25

AMOUNT_ETH_PER_TARGET   = Web3.to_wei("0.1", "ether")
BRIDGE_FRACTION         = 0.5
DEPOSIT_ETH_AMOUNT   = Web3.to_wei("0.0002", "ether")
WITHDRAW_ETH_AMOUNT  = Web3.to_wei("0.0001", "ether")
ERC20_AMOUNT         = 10 * 10**18

L1_EXPLORER_TX = "https://sepolia.etherscan.io/tx/"
L2_EXPLORER_TX = "https://sepolia-explorer.giwa.io/tx/"
L2_EXPLORER_ADDR = "https://sepolia-explorer.giwa.io/address/"

# ========================
# ABIs
# ========================

# 更新ERC-20 ABI，添加claimFaucet功能
ERC20_ABI = [
    {"name":"decimals","outputs":[{"type":"uint8","name":""}],"inputs":[],"stateMutability":"view","type":"function"},
    {"name":"balanceOf","outputs":[{"type":"uint256","name":""}],"inputs":[{"name":"owner","type":"address"}],"stateMutability":"view","type":"function"},
    {"name":"allowance","outputs":[{"type":"uint256","name":""}],"inputs":[{"name":"owner","type":"address"},{"name":"spender","type":"address"}],"stateMutability":"view","type":"function"},
    {"name":"approve","outputs":[{"type":"bool","name":""}],"inputs":[{"name":"spender","type":"address"},{"name":"value","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},
    {"name":"claimFaucet","outputs":[],"inputs":[],"stateMutability":"nonpayable","type":"function"},
    {"name":"transfer","outputs":[{"type":"bool","name":""}],"inputs":[{"name":"to","type":"address"},{"name":"amount","type":"uint256"}],"stateMutability":"nonpayable","type":"function"}
]

L1_STANDARD_BRIDGE_ABI = [
    {
        "inputs":[
            {"internalType":"address","name":"_to","type":"address"},
            {"internalType":"uint32","name":"_l2Gas","type":"uint32"},
            {"internalType":"bytes","name":"_data","type":"bytes"}],
        "name":"depositETHTo","outputs":[],"stateMutability":"payable","type":"function"
    },
    {
        "inputs":[
            {"internalType":"address","name":"_l1Token","type":"address"},
            {"internalType":"address","name":"_l2Token","type":"address"},
            {"internalType":"address","name":"_to","type":"address"},
            {"internalType":"uint256","name":"_amount","type":"uint256"},
            {"internalType":"uint32","name":"_l2Gas","type":"uint32"},
            {"internalType":"bytes","name":"_data","type":"bytes"}],
        "name":"depositERC20To","outputs":[],"stateMutability":"nonpayable","type":"function"
    }
]

L2_STANDARD_BRIDGE_ABI = [
    {
        "inputs":[
            {"internalType":"address","name":"_l2Token","type":"address"},
            {"internalType":"uint256","name":"_amount","type":"uint256"},
            {"internalType":"uint32","name":"_minGasLimit","type":"uint32"},
            {"internalType":"bytes","name":"_extraData","type":"bytes"}],
        "name":"withdraw","outputs":[],"stateMutability":"nonpayable","type":"function"
    }
]

L2_MESSAGE_PASSER_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "_target", "type": "address"},
            {"internalType": "uint256", "name": "_gasLimit", "type": "uint256"},
            {"internalType": "bytes",   "name": "_data",     "type": "bytes"}
        ],
        "name": "initiateWithdrawal",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    }
]

# ========================
# 日志配置
# ========================

class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""
    
    COLORS = {
        'DEBUG': Fore.WHITE,
        'INFO': Fore.BLUE,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.MAGENTA
    }
    
    def format(self, record):
        color = self.COLORS.get(record.levelname, Fore.WHITE)
        record.levelname = f"{color}{record.levelname}{Style.RESET_ALL}"
        return super().format(record)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# 如果支持彩色，使用彩色格式化器
if COLORS_ENABLED:
    for handler in logging.getLogger().handlers:
        handler.setFormatter(ColoredFormatter("%(asctime)s | %(levelname)s | %(message)s"))

log = logging.getLogger("giwa-bot")

# ========================
# 核心工具函数
# ========================

def load_first_private_key(file_path: str = "add.txt") -> LocalAccount:
    """加载第一个私钥"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"未找到私钥文件 {file_path}")
    
    print_step("LOAD", f"从 {file_path} 加载私钥...")
    
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            if not s.startswith("0x"):
                s = "0x" + s
            acct = Account.from_key(s)
            print_success(f"已加载账户: {format_address(acct.address)}")
            return acct
    raise RuntimeError("add.txt 未读取到有效私钥")

def load_all_accounts(file_path: str = "add.txt") -> List[LocalAccount]:
    """读取所有私钥"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"未找到私钥文件 {file_path}")
    
    accts: List[LocalAccount] = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            if not s.startswith("0x"):
                s = "0x" + s
            try:
                acct = Account.from_key(s)
                accts.append(acct)
                print_step("LOAD", f"账户 {line_num}: {format_address(acct.address)}")
            except Exception as e:
                print_warning(f"第 {line_num} 行私钥格式错误，已跳过")
    
    if len(accts) < 2:
        raise RuntimeError("需要至少两个私钥（第一个为源账户，其余为接收账户）")
    
    print_success(f"共加载 {len(accts)} 个账户")
    return accts

@dataclass
class Chain:
    name: str
    rpc: str
    w3: Web3
    account: LocalAccount
    nonce: int

def make_w3(rpc: str) -> Web3:
    """创建 Web3 实例"""
    print_step("CONNECT", f"连接到 RPC: {rpc}")
    w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 30}))
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    if not w3.is_connected():
        raise RuntimeError(f"RPC 无法连接：{rpc}")
    print_success("RPC 连接成功")
    return w3

def fee_profile(chain_name: str) -> Tuple[float, float]:
    """获取链的费用配置"""
    if chain_name.startswith("GIWA"):
        return 2.0, 2.5
    else:
        return 8.0, 4.0

def get_eip1559_fees(w3: Web3, tip_gwei: float, max_multiplier: float) -> Tuple[int,int,int]:
    """获取 EIP-1559 费用"""
    try:
        base = w3.eth.fee_history(1, "latest")["baseFeePerGas"][-1]
    except Exception:
        base = w3.to_wei(2, "gwei")
    priority = Web3.to_wei(tip_gwei, "gwei")
    max_fee = int(base * max_multiplier + priority * 2)
    return base, priority, max_fee

def wait_receipt_with_progress(w3: Web3, tx_hash: str, timeout: int = TX_WAIT_TIMEOUT):
    """等待交易回执并显示进度"""
    print_step("WAIT", f"等待交易确认: {tx_hash[:10]}...")
    start = time.time()
    last_err = None
    
    while time.time() - start < timeout:
        try:
            rcpt = w3.eth.get_transaction_receipt(tx_hash)
            if rcpt:
                if rcpt["status"] == 1:
                    print_success(f"交易确认成功! Gas 使用: {rcpt['gasUsed']:,}")
                else:
                    print_error("交易失败!")
                return rcpt
        except Exception as e:
            last_err = e
        
        # 显示等待进度
        elapsed = int(time.time() - start)
        print(f"\r{Fore.BLUE}⏳ 等待中... {elapsed}s / {timeout}s{Style.RESET_ALL}", end="", flush=True)
        time.sleep(TX_POLL_INTERVAL)
    
    print()  # 换行
    if last_err:
        print_warning(f"等待回执超时（最后错误：{last_err}）")
    return None

def estimate_and_cap_gas(w3: Web3, tx: Dict[str,Any], default_cap: int) -> int:
    """估算并限制 Gas"""
    try:
        est = w3.eth.estimate_gas(tx)
        gas = int(est * 1.15)
        estimated_gas = min(gas, default_cap)
        print_step("GAS", f"估算 Gas: {est:,} → 使用: {estimated_gas:,}")
        return estimated_gas
    except Exception:
        print_warning(f"Gas 估算失败，使用默认值: {default_cap:,}")
        return default_cap

def ensure_funds_for_tx(w3: Web3, addr: str, value: int, gas: int, max_fee_per_gas: int) -> bool:
    """检查账户余额是否足够"""
    bal = w3.eth.get_balance(addr)
    worst_cost = value + gas * max_fee_per_gas
    
    print_step("BALANCE", f"当前余额: {format_eth(bal)}")
    print_step("COST", f"预估成本: {format_eth(worst_cost)} (含最大 Gas 费)")
    
    if bal >= worst_cost:
        print_success("余额充足")
        return True
    else:
        print_error(f"余额不足! 缺少: {format_eth(worst_cost - bal)}")
        return False

def wait_for_l2_credit(l2: Chain, before_balance: int, expect_min_delta_wei: int = Web3.to_wei("0.00015","ether"), timeout: int = 300):
    """等待 L2 入账"""
    print_section_header("等待 L2 资金入账")
    print_step("WAIT", "监控 L2 余额变化（最多 5 分钟）...")
    
    start = time.time()
    dots = 0
    while time.time() - start < timeout:
        now = l2.w3.eth.get_balance(l2.account.address)
        delta = now - before_balance
        
        if delta >= expect_min_delta_wei:
            print_success(f"L2 余额已增加: +{format_eth(delta)}")
            return True
        
        # 显示等待动画
        elapsed = int(time.time() - start)
        dots = (dots + 1) % 4
        print(f"\r{Fore.BLUE}⏳ 等待入账{'.' * dots}{' ' * (3-dots)} {elapsed}s/{timeout}s{Style.RESET_ALL}", end="", flush=True)
        time.sleep(5)
    
    print()
    print_warning("未检测到明显入账（可能是索引延迟或金额较小）")
    return False

def build_and_send(chain: Chain, tx: Dict[str, Any], allow_speedup: bool = False) -> str:
    """构建并发送交易"""
    tip_gwei, max_mult = fee_profile(chain.name)
    base, tip, max_fee = get_eip1559_fees(chain.w3, tip_gwei, max_mult)

    tx.setdefault("maxPriorityFeePerGas", tip)
    tx.setdefault("maxFeePerGas", max_fee)
    tx.setdefault("chainId", chain.w3.eth.chain_id)
    tx.setdefault("nonce", chain.nonce)

    if "gas" not in tx:
        default_cap = 700_000 if (tx.get("data") and len(tx.get("data")) > 2) else 300_000
        try:
            tx_for_est = {**tx, "from": chain.account.address}
            tx["gas"] = estimate_and_cap_gas(chain.w3, tx_for_est, default_cap)
        except Exception:
            tx["gas"] = default_cap

    if chain.name.startswith("GIWA"):
        ok = ensure_funds_for_tx(chain.w3, chain.account.address, tx.get("value",0), tx["gas"], tx["maxFeePerGas"])
        if not ok:
            bal_before = chain.w3.eth.get_balance(chain.account.address)
            print_warning("L2 余额暂不足，等待可能的 L1→L2 入账...")
            wait_for_l2_credit(chain, bal_before)
            ok_again = ensure_funds_for_tx(chain.w3, chain.account.address, tx.get("value",0), tx["gas"], tx["maxFeePerGas"])
            if not ok_again:
                raise RuntimeError("L2 余额仍不足以覆盖交易成本")

    signed = chain.account.sign_transaction(tx)
    try:
        h = chain.w3.eth.send_raw_transaction(signed.rawTransaction).hex()
        chain.nonce += 1
        print_step("SEND", f"交易已发送: {h[:10]}...")
        return h
    except Exception as e:
        if allow_speedup and ("underpriced" in str(e) or "replacement transaction underpriced" in str(e)):
            print_warning("交易费用过低，自动提速重发...")
            tx["maxPriorityFeePerGas"] = int(tx["maxPriorityFeePerGas"] * REPLACE_BUMP)
            tx["maxFeePerGas"]        = int(tx["maxFeePerGas"]        * REPLACE_BUMP)
            signed = chain.account.sign_transaction(tx)
            h = chain.w3.eth.send_raw_transaction(signed.rawTransaction).hex()
            chain.nonce += 1
            print_success("提速交易已发送")
            return h
        raise

# ========================
# ERC-20 智能管理函数
# ========================

def check_and_claim_erc20_balance(chain: Chain, token_address: str, required_amount: int, token_name: str) -> bool:
    """检查ERC20代币余额，如果不足则尝试领取"""
    print_step("CHECK", f"检查 {token_name} 代币余额...")
    
    contract = chain.w3.eth.contract(address=token_address, abi=ERC20_ABI)
    balance = contract.functions.balanceOf(chain.account.address).call()
    
    # 获取代币小数位数
    try:
        decimals = contract.functions.decimals().call()
    except:
        decimals = 18  # 默认18位小数
    
    balance_formatted = balance / (10 ** decimals)
    required_formatted = required_amount / (10 ** decimals)
    
    print_step("BALANCE", f"当前余额: {balance_formatted:.6f} {token_name}")
    print_step("REQUIRED", f"需要余额: {required_formatted:.6f} {token_name}")
    
    if balance >= required_amount:
        print_success(f"{token_name} 余额充足")
        return True
    
    print_warning(f"{token_name} 余额不足，尝试从水龙头领取...")
    
    # 尝试调用 claimFaucet 函数
    try:
        print_step("FAUCET", "调用 claimFaucet 函数...")
        tx = contract.functions.claimFaucet().build_transaction({"from": chain.account.address})
        tx_hash = build_and_send(chain, tx, allow_speedup=True)
        print_info(f"Faucet 交易: {L1_EXPLORER_TX}{tx_hash}")
        
        rcpt = wait_receipt_with_progress(chain.w3, tx_hash)
        if not rcpt or rcpt["status"] != 1:
            print_error("水龙头领取失败")
            return False
        
        print_success("水龙头领取成功！")
        
        # 重新检查余额
        time.sleep(3)  # 等待余额更新
        new_balance = contract.functions.balanceOf(chain.account.address).call()
        new_balance_formatted = new_balance / (10 ** decimals)
        
        print_step("NEW_BALANCE", f"更新后余额: {new_balance_formatted:.6f} {token_name}")
        
        if new_balance >= required_amount:
            print_success(f"{token_name} 余额现已充足")
            return True
        else:
            print_warning(f"{token_name} 余额仍然不足，但可以尝试继续")
            return new_balance > 0  # 至少有一些余额就继续
            
    except Exception as e:
        print_error(f"水龙头领取失败: {e}")
        print_warning("可能原因:")
        print_warning("1. 该合约没有 claimFaucet 函数")
        print_warning("2. 已经领取过，有冷却时间限制")
        print_warning("3. 水龙头已经耗尽")
        print_warning("4. 网络或合约问题")
        
        # 即使领取失败，如果有任何余额也尝试继续
        if balance > 0:
            print_info(f"使用现有余额 {balance_formatted:.6f} {token_name} 继续")
            return True
        
        return False

def get_erc20_balance(chain: Chain, token_address: str) -> tuple[int, int]:
    """获取ERC20代币余额和小数位数"""
    contract = chain.w3.eth.contract(address=token_address, abi=ERC20_ABI)
    balance = contract.functions.balanceOf(chain.account.address).call()
    
    try:
        decimals = contract.functions.decimals().call()
    except:
        decimals = 18
    
    return balance, decimals

def ensure_allowance(chain: Chain, token: str, spender: str, min_amount: int) -> Optional[str]:
    """确保代币授权额度"""
    print_step("APPROVE", "检查代币授权额度...")
    c = chain.w3.eth.contract(address=token, abi=ERC20_ABI)
    current = c.functions.allowance(chain.account.address, spender).call()
    
    # 获取代币信息用于显示
    try:
        decimals = c.functions.decimals().call()
    except:
        decimals = 18
    
    current_formatted = current / (10 ** decimals)
    min_formatted = min_amount / (10 ** decimals)
    
    print_step("ALLOWANCE", f"当前授权额度: {current_formatted:.6f}")
    print_step("REQUIRED", f"需要授权额度: {min_formatted:.6f}")
    
    if current >= min_amount:
        print_success("授权额度充足")
        return None
    
    print_step("APPROVE", f"需要授权 {min_formatted:.6f} 代币给 {format_address(spender)}")
    
    # 授权一个较大的金额以避免频繁授权
    approve_amount = max(min_amount * 10, Web3.to_wei("1000000", "ether"))  # 授权较大金额
    
    tx = c.functions.approve(spender, approve_amount).build_transaction({"from": chain.account.address})
    tx_hash = build_and_send(chain, tx, allow_speedup=True)
    rcpt = wait_receipt_with_progress(chain.w3, tx_hash)
    
    if not rcpt or rcpt["status"] != 1:
        raise RuntimeError("代币授权失败")
    
    print_success("代币授权完成")
    return tx_hash

# ========================
# 桥接功能
# ========================

def deposit_erc20_to_l2(l1: Chain, l2: Chain, l1_token: str, l2_token: str, amount: int):
    """Sepolia ERC-20 桥接到 Giwa ERC-20"""
    print_section_header("Sepolia ERC-20 → Giwa ERC-20")
    
    # 1. 检查并领取L1代币
    if not check_and_claim_erc20_balance(l1, l1_token, amount, "L1 ERC-20"):
        raise RuntimeError("L1 ERC-20 代币余额不足且无法领取")
    
    # 2. 显示实际可用余额，如果不足则使用实际余额
    actual_balance, decimals = get_erc20_balance(l1, l1_token)
    if actual_balance < amount:
        print_warning(f"实际余额少于预期，使用实际余额进行桥接")
        amount = actual_balance
        if amount == 0:
            raise RuntimeError("L1 ERC-20 代币余额为零")
    
    amount_formatted = amount / (10 ** decimals)
    print_step("BRIDGE", f"桥接金额: {amount_formatted:.6f} ERC-20")
    
    # 3. 检查并设置授权
    ensure_allowance(l1, l1_token, ADDR_L1_STANDARD_BRIDGE, amount)
    
    # 4. 执行桥接
    bridge = l1.w3.eth.contract(address=ADDR_L1_STANDARD_BRIDGE, abi=L1_STANDARD_BRIDGE_ABI)
    tx = bridge.functions.depositERC20To(
        l1_token, l2_token, l2.account.address, amount, DEFAULT_L2_GAS_LIMIT_MSG, b""
    ).build_transaction({"from": l1.account.address})
    
    tx_hash = build_and_send(l1, tx, allow_speedup=True)
    print_info(f"L1 交易链接: {L1_EXPLORER_TX}{tx_hash}")
    
    rcpt = wait_receipt_with_progress(l1.w3, tx_hash)
    if not rcpt or rcpt["status"] != 1:
        raise RuntimeError("ERC-20 桥接失败")
    
    print_success("ERC-20 桥接初始化完成，L2 余额几分钟内到账")
    
    # 5. 显示桥接后余额
    time.sleep(2)
    remaining_balance, _ = get_erc20_balance(l1, l1_token)
    remaining_formatted = remaining_balance / (10 ** decimals)
    print_step("REMAINING", f"L1 剩余余额: {remaining_formatted:.6f} ERC-20")

def withdraw_eth_to_l1_via_message_passer(l2: Chain, l1: Chain, amount_wei: int):
    """Giwa ETH 桥接到 Sepolia ETH"""
    print_section_header("Giwa ETH → Sepolia ETH")
    
    mp = l2.w3.eth.contract(address=ADDR_L2_MESSAGE_PASSER, abi=L2_MESSAGE_PASSER_ABI)
    tx = mp.functions.initiateWithdrawal(
        l1.account.address, 0, b""
    ).build_transaction({"from": l2.account.address, "value": amount_wei})
    
    tx_hash = build_and_send(l2, tx, allow_speedup=True)
    print_info(f"L2 交易链接: {L2_EXPLORER_TX}{tx_hash}")
    
    rcpt = wait_receipt_with_progress(l2.w3, tx_hash)
    if not rcpt or rcpt["status"] != 1:
        raise RuntimeError("ETH 提现初始化失败")
    
    print_success("ETH 提现初始化完成")
    print_warning("需等待约7天挑战期后在 L1 完成 prove/finalize")

def withdraw_erc20_to_l1(l2: Chain, l1: Chain, l2_token: str, amount: int):
    """Giwa ERC-20 桥接到 Sepolia ERC-20"""
    print_section_header("Giwa ERC-20 → Sepolia ERC-20")
    
    # 1. 检查L2代币余额
    actual_balance, decimals = get_erc20_balance(l2, l2_token)
    
    if actual_balance == 0:
        print_warning("L2 ERC-20 代币余额为零")
        print_info("尝试先在 L1 领取代币，然后桥接到 L2...")
        
        # 尝试在L1领取代币并桥接到L2
        try:
            # 检查L1余额是否足够支付gas
            l1_eth_balance = l1.w3.eth.get_balance(l2.account.address)
            if l1_eth_balance < Web3.to_wei("0.01", "ether"):
                raise RuntimeError("L1 ETH 余额不足，无法执行代币领取和桥接操作")
            
            print_step("AUTO", "自动执行 L1 代币领取 → L2 桥接流程")
            
            # 创建临时的L1链对象用于操作
            temp_l1 = Chain(
                name=l1.name, 
                rpc=l1.rpc, 
                w3=l1.w3, 
                account=l2.account,  # 使用相同的账户
                nonce=l1.w3.eth.get_transaction_count(l2.account.address, "pending")
            )
            
            # 尝试领取L1代币
            if check_and_claim_erc20_balance(temp_l1, ADDR_L1_ERC20, amount, "L1 ERC-20"):
                print_step("AUTO", "L1代币领取成功，开始桥接到L2...")
                
                # 获取实际L1代币余额
                l1_token_balance, _ = get_erc20_balance(temp_l1, ADDR_L1_ERC20)
                if l1_token_balance > 0:
                    # 使用较小的金额进行桥接，避免全部用完
                    bridge_amount = min(l1_token_balance, amount)
                    
                    # 创建临时L2对象
                    temp_l2 = Chain(
                        name=l2.name, 
                        rpc=l2.rpc, 
                        w3=l2.w3, 
                        account=l2.account,
                        nonce=l2.w3.eth.get_transaction_count(l2.account.address, "pending")
                    )
                    
                    # 执行L1→L2桥接
                    deposit_erc20_to_l2(temp_l1, temp_l2, ADDR_L1_ERC20, l2_token, bridge_amount)
                    
                    print_success("自动桥接完成，等待L2代币到账...")
                    print_warning("L2代币通常需要5-15分钟到账，请稍后重试此操作")
                    return
            
        except Exception as e:
            print_error(f"自动领取和桥接失败: {e}")
        
        # 如果自动流程失败，提供手动建议
        print_warning("自动处理失败，请手动执行以下步骤：")
        print_info("1. 使用菜单项 [6] 领取 L1 测试代币")
        print_info("2. 使用菜单项 [2] 将 L1 ERC-20 桥接到 L2")
        print_info("3. 等待5-15分钟后再尝试 L2→L1 提现")
        raise RuntimeError("L2 ERC-20 代币余额不足，已尝试自动获取但失败")
    
    # 如果余额不足，使用实际余额
    if actual_balance < amount:
        print_warning(f"L2代币余额不足，使用实际余额进行提现")
        amount = actual_balance
    
    amount_formatted = amount / (10 ** decimals)
    actual_formatted = actual_balance / (10 ** decimals)
    
    print_step("L2_BALANCE", f"L2 代币余额: {actual_formatted:.6f} ERC-20")
    print_step("WITHDRAW", f"提现金额: {amount_formatted:.6f} ERC-20")
    
    # 2. 执行L2提现
    bridge = l2.w3.eth.contract(address=ADDR_L2_STANDARD_BRIDGE, abi=L2_STANDARD_BRIDGE_ABI)
    tx = bridge.functions.withdraw(
        l2_token, amount, 0, b""
    ).build_transaction({"from": l2.account.address})
    
    tx_hash = build_and_send(l2, tx, allow_speedup=True)
    print_info(f"L2 交易链接: {L2_EXPLORER_TX}{tx_hash}")
    
    rcpt = wait_receipt_with_progress(l2.w3, tx_hash)
    if not rcpt or rcpt["status"] != 1:
        raise RuntimeError("ERC-20 提现初始化失败")
    
    print_success("ERC-20 提现初始化完成，需在 L1 完成最终确认")
    print_warning("完整提现流程需要约7天挑战期，然后在L1执行prove和finalize")
    
    # 3. 显示提现后余额
    time.sleep(2)
    remaining_balance, _ = get_erc20_balance(l2, l2_token)
    remaining_formatted = remaining_balance / (10 ** decimals)
    print_step("REMAINING", f"L2 剩余余额: {remaining_formatted:.6f} ERC-20")

def claim_test_tokens_generic(chain: Chain, token_addr: str, explorer_tx: str, network_name: str):
    """通用领取测试代币函数"""
    print_section_header(f"🪙 领取{network_name}测试代币")
    
    print_step("INFO", f"从 {network_name} 测试代币水龙头领取代币")
    print_step("CONTRACT", f"{network_name} 代币合约: {format_address(token_addr)}")
    
    # 检查当前余额
    current_balance, decimals = get_erc20_balance(chain, token_addr)
    current_formatted = current_balance / (10 ** decimals)
    print_step("CURRENT", f"当前余额: {current_formatted:.6f} TEST")
    
    try:
        # 调用 claimFaucet
        contract = chain.w3.eth.contract(address=token_addr, abi=ERC20_ABI)
        tx = contract.functions.claimFaucet().build_transaction({"from": chain.account.address})
        tx_hash = build_and_send(chain, tx, allow_speedup=True)
        print_info(f"领取交易: {explorer_tx}{tx_hash}")
        
        rcpt = wait_receipt_with_progress(chain.w3, tx_hash)
        if not rcpt or rcpt["status"] != 1:
            raise RuntimeError("代币领取失败")
        
        print_success("代币领取成功！")
        
        # 显示新余额
        time.sleep(3)
        new_balance, _ = get_erc20_balance(chain, token_addr)
        new_formatted = new_balance / (10 ** decimals)
        received = (new_balance - current_balance) / (10 ** decimals)
        
        print_step("NEW_BALANCE", f"更新后余额: {new_formatted:.6f} TEST")
        print_step("RECEIVED", f"本次领取: {received:.6f} TEST")
        
        if received > 0:
            print_success("🎉 成功领取测试代币！")
        else:
            print_warning("未检测到余额增加，可能已在冷却期内")
            
    except Exception as e:
        print_error(f"代币领取失败: {e}")
        print_warning("可能的原因：")
        print_warning("• 冷却时间未到（通常24小时一次）")
        print_warning("• 水龙头已耗尽")
        print_warning("• 网络拥堵或Gas不足")
        print_info("可以尝试稍后再试，或检查区块链浏览器确认交易状态")

def claim_test_tokens_menu(l1: Chain, l2: Chain, all_accounts: List[LocalAccount]):
    """领取测试代币菜单，支持L1/L2和批量"""
    print_section_header("🪙 领取测试代币")
    
    # 选择网络
    print(f"{Fore.CYAN}请选择网络:{Style.RESET_ALL}")
    print("1. L1 (Sepolia)")
    print("2. L2 (Giwa)")
    print("3. Both (L1 and L2)")
    choice_net = input(f"{Fore.YELLOW}选择 (1/2/3): {Style.RESET_ALL}").strip()
    
    if choice_net not in ['1', '2', '3']:
        print_error("无效选择")
        return
    
    # 选择账户范围
    print(f"\n{Fore.CYAN}请选择账户范围:{Style.RESET_ALL}")
    print("1. 当前账户 (第一个账户)")
    print("2. 所有账户")
    choice_acc = input(f"{Fore.YELLOW}选择 (1/2): {Style.RESET_ALL}").strip()
    
    if choice_acc not in ['1', '2']:
        print_error("无效选择")
        return
    
    accounts_to_process = [l1.account] if choice_acc == '1' else all_accounts
    
    total_accounts = len(accounts_to_process)
    success_count = 0
    
    for idx, account in enumerate(accounts_to_process, 1):
        print(f"\n{Fore.MAGENTA}处理账户 [{idx}/{total_accounts}]: {format_address(account.address)}{Style.RESET_ALL}")
        
        # 为每个账户创建Chain对象
        account_l1 = Chain(
            name=l1.name,
            rpc=l1.rpc,
            w3=l1.w3,
            account=account,
            nonce=l1.w3.eth.get_transaction_count(account.address, "pending")
        )
        account_l2 = Chain(
            name=l2.name,
            rpc=l2.rpc,
            w3=l2.w3,
            account=account,
            nonce=l2.w3.eth.get_transaction_count(account.address, "pending")
        )
        
        try:
            if choice_net in ['1', '3']:
                claim_test_tokens_generic(account_l1, ADDR_L1_ERC20, L1_EXPLORER_TX, "L1")
            if choice_net in ['2', '3']:
                claim_test_tokens_generic(account_l2, ADDR_L2_ERC20, L2_EXPLORER_TX, "L2")
            success_count += 1
        except Exception as e:
            print_error(f"账户 {format_address(account.address)} 领取失败: {e}")
        
        if idx < total_accounts:
            time.sleep(random.randint(5, 15))  # 账户间暂停
    
    print_success(f"领取完成! 成功账户: {success_count}/{total_accounts}")

def l2_self_transfer_eth(l2: Chain, amount_wei: int):
    """L2 ETH 自转测试"""
    print_section_header(f"Giwa ETH 自转测试")
    print_step("TRANSFER", f"金额: {format_eth(amount_wei)}")
    
    tx = {"from": l2.account.address, "to": l2.account.address, "value": amount_wei}
    tx_hash = build_and_send(l2, tx, allow_speedup=True)
    print_info(f"交易链接: {L2_EXPLORER_TX}{tx_hash}")
    
    rcpt = wait_receipt_with_progress(l2.w3, tx_hash)
    if not rcpt or rcpt["status"] != 1:
        raise RuntimeError("ETH 自转失败")
    
    print_success("ETH 自转测试完成")

# ========================
# 智能合约部署
# ========================

def ensure_solc(required_version: str = "0.8.20"):
    """确保 solc 编译器可用"""
    if not SOLCX_AVAILABLE:
        raise RuntimeError("缺少 py-solc-x，请先安装：pip install py-solc-x")
    
    installed = [str(v) for v in get_installed_solc_versions()]
    print_step("SOLC", f"已安装版本: {installed}")
    
    if required_version not in installed:
        print_step("SOLC", f"安装 solc {required_version}...")
        install_solc(required_version)
        print_success(f"solc {required_version} 安装完成")
    
    set_solc_version(required_version)
    print_success(f"使用 solc {required_version}")

def compile_contract_src(name: str, source_code: str):
    """编译合约源码"""
    print_step("COMPILE", f"编译 {name}...")
    compiled = compile_source(source_code, output_values=["abi", "bin"])
    _, ci = compiled.popitem()
    abi = ci["abi"]
    bytecode = "0x" + ci["bin"]
    print_success(f"{name} 编译完成")
    return abi, bytecode

def l2_multi_deploy_test(l2: Chain):
    """L2 多合约部署测试"""
    print_section_header("Giwa 多合约部署测试")
    
    ensure_solc("0.8.20")

    # 合约样例
    samples = [
        ("🔹 Minimal 合约", """
            // SPDX-License-Identifier: MIT
            pragma solidity ^0.8.20;
            contract Minimal {}
        """, ()),
        
        ("📦 SimpleStorage 合约", """
            // SPDX-License-Identifier: MIT
            pragma solidity ^0.8.20;
            contract SimpleStorage {
                uint256 public value;
                function set(uint256 v) public { value = v; }
                function get() public view returns (uint256) { return value; }
            }
        """, ()),
        
        ("🪙 ERC20 代币", """
            // SPDX-License-Identifier: MIT
            pragma solidity ^0.8.20;
            contract ERC20Token {
                string public name = "TestToken";
                string public symbol = "TTK";
                uint8 public decimals = 18;
                uint256 public totalSupply;
                mapping(address => uint256) public balanceOf;
                event Transfer(address indexed from, address indexed to, uint256 value);
                constructor(uint256 initialSupply) {
                    totalSupply = initialSupply * 10 ** uint256(decimals);
                    balanceOf[msg.sender] = totalSupply;
                }
                function transfer(address to, uint256 value) public returns (bool) {
                    require(balanceOf[msg.sender] >= value, "No balance");
                    balanceOf[msg.sender] -= value;
                    balanceOf[to] += value;
                    emit Transfer(msg.sender, to, value);
                    return true;
                }
            }
        """, (1000,)),
        
        ("🎨 ERC721 NFT", """
            // SPDX-License-Identifier: MIT
            pragma solidity ^0.8.20;
            contract SimpleNFT {
                string public name = "SimpleNFT";
                string public symbol = "SNFT";
                uint256 public nextId = 1;
                mapping(uint256 => address) public ownerOf;
                event Transfer(address indexed from, address indexed to, uint256 indexed tokenId);
                function mint(address to) public {
                    ownerOf[nextId] = to;
                    emit Transfer(address(0), to, nextId);
                    nextId++;
                }
            }
        """, ()),
        
        ("🎭 ERC1155 MultiToken", """
            // SPDX-License-Identifier: MIT
            pragma solidity ^0.8.20;
            contract Simple1155 {
                mapping(uint256 => mapping(address => uint256)) public balanceOf;
                event TransferSingle(address indexed from, address indexed to, uint256 id, uint256 value);
                function mint(address to, uint256 id, uint256 amount) public {
                    balanceOf[id][to] += amount;
                    emit TransferSingle(msg.sender, to, id, amount);
                }
            }
        """, ()),
        
        ("🔒 TimeLock 锁仓", """
            // SPDX-License-Identifier: MIT
            pragma solidity ^0.8.20;
            contract TimeLock {
                uint256 public unlockTime;
                constructor(uint256 _unlockTime) payable {
                    require(_unlockTime > block.timestamp, "Too soon");
                    unlockTime = _unlockTime;
                }
                function withdraw(address payable to) public {
                    require(block.timestamp >= unlockTime, "Locked");
                    to.transfer(address(this).balance);
                }
            }
        """, (int(time.time()) + 3600,)),
        
        ("👥 MultiSig 钱包", f"""
            // SPDX-License-Identifier: MIT
            pragma solidity ^0.8.20;
            contract SimpleMultiSig {{
                address[2] public owners;
                uint public required = 2;
                mapping(uint => mapping(address => bool)) public approvals;
                uint public txCount;
                struct Transaction {{ address to; uint value; bool executed; }}
                mapping(uint => Transaction) public txs;

                constructor(address o1, address o2) {{
                    owners[0] = o1; owners[1] = o2;
                }}

                function submitTx(address to, uint value) public {{
                    txs[txCount] = Transaction(to, value, false);
                    txCount++;
                }}

                function approve(uint txId) public {{
                    approvals[txId][msg.sender] = true;
                }}

                function execute(uint txId) public {{
                    require(!txs[txId].executed, "done");
                    require(approvals[txId][owners[0]] && approvals[txId][owners[1]], "not enough approvals");
                    txs[txId].executed = true;
                    payable(txs[txId].to).transfer(txs[txId].value);
                }}
                receive() external payable {{}}
            }}
        """, (l2.account.address, l2.account.address))
    ]

    total_contracts = len(samples)
    deployed_count = 0
    
    for idx, (title, src, ctor_args) in enumerate(samples, 1):
        print_progress_bar(idx-1, total_contracts, f"部署中... {title}")
        
        try:
            abi, bytecode = compile_contract_src(title, src)
            contract = l2.w3.eth.contract(abi=abi, bytecode=bytecode)
            tx = contract.constructor(*ctor_args).build_transaction({"from": l2.account.address})
            tx_hash = build_and_send(l2, tx, allow_speedup=True)
            
            print_step("DEPLOY", f"{title} 部署中...")
            print_info(f"交易: {L2_EXPLORER_TX}{tx_hash}")
            
            rcpt = wait_receipt_with_progress(l2.w3, tx_hash)
            if not rcpt or rcpt["status"] != 1:
                print_error(f"{title} 部署失败")
                continue
                
            addr = rcpt["contractAddress"]
            print_success(f"{title} 部署成功")
            print_info(f"合约地址: {L2_EXPLORER_ADDR}{addr}")
            deployed_count += 1
            
        except Exception as e:
            print_error(f"{title} 部署失败: {e}")
            continue
    
    print_progress_bar(total_contracts, total_contracts, "完成")
    print_success(f"多合约部署测试完成! 成功: {deployed_count}/{total_contracts}")

# ========================
# 分发 + 桥接
# ========================

def distribute_and_bridge(l1: Chain, l2: Chain, all_accounts: List[LocalAccount]):
    """批量分发和桥接"""
    if len(all_accounts) < 2:
        raise RuntimeError("需要至少两个私钥（第一个为源账户，其余为接收账户）")

    source_addr = l1.account.address
    targets = [acct.address for acct in all_accounts[1:]]

    print_section_header("批量分发 + 桥接")
    print_step("SOURCE", f"源账户: {format_address(source_addr)}")
    print_step("BALANCE", f"L1 余额: {format_eth(l1.w3.eth.get_balance(source_addr))}")
    print_step("TARGETS", f"目标地址: {len(targets)} 个")
    print_step("AMOUNTS", f"每个地址分发: {format_eth(AMOUNT_ETH_PER_TARGET)}")
    print_step("BRIDGE", f"每个地址桥接: {format_eth(int(AMOUNT_ETH_PER_TARGET * BRIDGE_FRACTION))}")

    # 费用计算
    tip_gwei, max_mult = fee_profile(l1.name)
    _, priority, max_fee = get_eip1559_fees(l1.w3, tip_gwei, max_mult)
    bridge = l1.w3.eth.contract(address=ADDR_L1_STANDARD_BRIDGE, abi=L1_STANDARD_BRIDGE_ABI)

    total_operations = len(targets) * 2  # 每个目标地址需要转账+桥接
    current_op = 0

    for idx, to_addr in enumerate(targets, 1):
        print(f"\n{Fore.MAGENTA}{'─'*60}")
        print(f"处理目标 [{idx}/{len(targets)}]: {format_address(to_addr)}")
        print(f"{'─'*60}{Style.RESET_ALL}")

        # 1) L1 转账
        current_op += 1
        print_progress_bar(current_op-1, total_operations, f"L1 转账到 {format_address(to_addr)}")
        
        tx1 = {
            "from": source_addr,
            "to": to_addr,
            "value": AMOUNT_ETH_PER_TARGET,
            "chainId": l1.w3.eth.chain_id,
            "nonce": l1.nonce,
            "maxPriorityFeePerGas": priority,
            "maxFeePerGas": max_fee,
            "gas": 21000  # 标准转账
        }

        if not ensure_funds_for_tx(l1.w3, source_addr, tx1["value"], tx1["gas"], tx1["maxFeePerGas"]):
            raise RuntimeError("L1 余额不足")

        signed1 = l1.account.sign_transaction(tx1)
        try:
            h1 = l1.w3.eth.send_raw_transaction(signed1.rawTransaction).hex()
        except Exception as e:
            if "underpriced" in str(e):
                tx1["maxPriorityFeePerGas"] = int(tx1["maxPriorityFeePerGas"] * REPLACE_BUMP)
                tx1["maxFeePerGas"] = int(tx1["maxFeePerGas"] * REPLACE_BUMP)
                signed1 = l1.account.sign_transaction(tx1)
                h1 = l1.w3.eth.send_raw_transaction(signed1.rawTransaction).hex()
            else:
                raise
        
        l1.nonce += 1
        print_step("TX1", f"L1 转账: {L1_EXPLORER_TX}{h1}")
        
        rcpt1 = wait_receipt_with_progress(l1.w3, h1)
        if not rcpt1 or rcpt1["status"] != 1:
            print_error("L1 转账失败")
            continue

        # 2) L1→L2 桥接
        current_op += 1
        print_progress_bar(current_op-1, total_operations, f"桥接到 {format_address(to_addr)}")
        
        bridge_amount = int(AMOUNT_ETH_PER_TARGET * BRIDGE_FRACTION)
        tx2 = bridge.functions.depositETHTo(
            to_addr, DEFAULT_L2_GAS_LIMIT_MSG, b""
        ).build_transaction({
            "from": source_addr, 
            "value": bridge_amount, 
            "nonce": l1.nonce, 
            "chainId": l1.w3.eth.chain_id,
            "maxPriorityFeePerGas": priority,
            "maxFeePerGas": max_fee
        })

        if "gas" not in tx2:
            tx2["gas"] = estimate_and_cap_gas(l1.w3, {**tx2, "from": source_addr}, 300_000)

        if not ensure_funds_for_tx(l1.w3, source_addr, tx2["value"], tx2["gas"], tx2["maxFeePerGas"]):
            print_error("L1 余额不足以完成桥接")
            continue

        signed2 = l1.account.sign_transaction(tx2)
        try:
            h2 = l1.w3.eth.send_raw_transaction(signed2.rawTransaction).hex()
        except Exception as e:
            if "underpriced" in str(e):
                tx2["maxPriorityFeePerGas"] = int(tx2["maxPriorityFeePerGas"] * REPLACE_BUMP)
                tx2["maxFeePerGas"] = int(tx2["maxFeePerGas"] * REPLACE_BUMP)
                signed2 = l1.account.sign_transaction(tx2)
                h2 = l1.w3.eth.send_raw_transaction(signed2.rawTransaction).hex()
            else:
                raise
        
        l1.nonce += 1
        print_step("TX2", f"L1 桥接: {L1_EXPLORER_TX}{h2}")
        
        rcpt2 = wait_receipt_with_progress(l1.w3, h2)
        if not rcpt2 or rcpt2["status"] != 1:
            print_error("L1→L2 桥接失败")
            continue
            
        print_success(f"目标 {idx} 处理完成")

    print_progress_bar(total_operations, total_operations, "全部完成")
    print_success(f"批量分发+桥接完成! L2 余额将在几分钟内到账")

# ========================
# 一键全流程
# ========================

def one_click_flow_random(l1: Chain, l2: Chain, all_accounts: List[LocalAccount]):
    """一键随机全流程测试 - 24小时循环模式"""
    print_section_header("🎲 一键随机全流程测试 - 24小时循环模式")
    
    print_step("MODE", "多地址循环测试模式")
    print_step("ACCOUNTS", f"将测试 {len(all_accounts)} 个地址")
    print_step("CYCLE", "每24小时执行一次完整循环")
    
    # 询问用户是否启动24小时循环
    try:
        choice = input(f"\n{Fore.YELLOW}是否启动24小时循环模式？[y/N]: {Style.RESET_ALL}").strip().lower()
        if choice not in ['y', 'yes']:
            print_info("执行单次全流程测试")
            run_single_cycle(l1, l2, all_accounts)
            return
    except (EOFError, KeyboardInterrupt):
        print_info("执行单次全流程测试")
        run_single_cycle(l1, l2, all_accounts)
        return
    
    print_success("启动24小时循环模式...")
    print_warning("按 Ctrl+C 可以安全退出循环")
    
    cycle_count = 1
    try:
        while True:
            print_section_header(f"🔄 第 {cycle_count} 轮循环开始")
            current_time = time.strftime("%Y-%m-%d %H:%M:%S")
            print_step("TIME", f"开始时间: {current_time}")
            
            try:
                run_single_cycle(l1, l2, all_accounts)
                print_success(f"第 {cycle_count} 轮循环完成")
            except Exception as e:
                print_error(f"第 {cycle_count} 轮循环出错: {e}")
            
            cycle_count += 1
            
            # 24小时倒计时
            print_section_header("⏰ 等待下次循环")
            countdown_24_hours()
            
    except KeyboardInterrupt:
        print_warning("\n用户中断，退出24小时循环模式")
        print_info(f"已完成 {cycle_count - 1} 轮循环")

def run_single_cycle(l1: Chain, l2: Chain, all_accounts: List[LocalAccount]):
    """执行单次完整循环"""
    
    # 基础任务模板
    base_tasks = [
        ("🪙 Sepolia ERC-20 → Giwa ERC-20", "deposit_erc20"),
        ("💰 Giwa ETH → Sepolia ETH", "withdraw_eth"),
        ("🔄 Giwa ERC-20 → Sepolia ERC-20", "withdraw_erc20"),
        ("🔁 Giwa ETH 自转测试", "self_transfer"),
    ]
    
    # 全局任务（只执行一次）
    global_tasks = [
        ("🚀 多合约部署测试", "deploy_contracts"),
    ]
    
    total_accounts = len(all_accounts)
    total_tasks_per_account = len(base_tasks)
    total_global_tasks = len(global_tasks)
    total_operations = total_accounts * total_tasks_per_account + total_global_tasks
    
    print_step("PLAN", f"计划执行 {total_operations} 个操作")
    print_step("BREAKDOWN", f"{total_accounts} 地址 × {total_tasks_per_account} 任务 + {total_global_tasks} 全局任务")
    
    current_op = 0
    success_count = 0
    failed_accounts = []
    
    # 为每个账户执行测试
    for account_idx, account in enumerate(all_accounts, 1):
        account_address = account.address
        print(f"\n{Fore.MAGENTA}{'='*70}")
        print(f"🎯 测试账户 [{account_idx}/{total_accounts}]: {format_address(account_address)}")
        print(f"{'='*70}{Style.RESET_ALL}")
        
        # 创建该账户的链对象
        account_l1 = Chain(
            name=l1.name, 
            rpc=l1.rpc, 
            w3=l1.w3, 
            account=account,
            nonce=l1.w3.eth.get_transaction_count(account.address, "pending")
        )
        account_l2 = Chain(
            name=l2.name, 
            rpc=l2.rpc, 
            w3=l2.w3, 
            account=account,
            nonce=l2.w3.eth.get_transaction_count(account.address, "pending")
        )
        
        # 检查账户余额
        l1_balance = account_l1.w3.eth.get_balance(account.address)
        l2_balance = account_l2.w3.eth.get_balance(account.address)
        
        print_step("BALANCE", f"L1: {format_eth(l1_balance)}, L2: {format_eth(l2_balance)}")
        
        # 如果余额太低，跳过该账户
        min_l1_balance = Web3.to_wei("0.01", "ether")  # 至少0.01 ETH
        min_l2_balance = Web3.to_wei("0.005", "ether")  # 至少0.005 ETH
        
        if l1_balance < min_l1_balance and l2_balance < min_l2_balance:
            print_warning(f"账户余额过低，跳过测试")
            failed_accounts.append((account_address, "余额不足"))
            current_op += total_tasks_per_account
            continue
        
        # 随机化任务顺序
        account_tasks = base_tasks.copy()
        random.shuffle(account_tasks)
        
        account_success = 0
        
        # 执行该账户的所有任务
        for task_idx, (task_name, task_type) in enumerate(account_tasks, 1):
            current_op += 1
            print_progress_bar(current_op-1, total_operations, f"{format_address(account_address)}: {task_name}")
            
            print(f"\n{Fore.CYAN}▶ [{task_idx}/{total_tasks_per_account}] {task_name}{Style.RESET_ALL}")
            
            try:
                # 根据任务类型执行相应功能
                if task_type == "deposit_erc20" and l1_balance >= min_l1_balance:
                    # 检查是否有L1 ERC-20代币，如果没有则尝试领取
                    l1_token_balance, _ = get_erc20_balance(account_l1, ADDR_L1_ERC20)
                    if l1_token_balance == 0:
                        print_step("AUTO", "检测到L1代币余额为零，尝试自动领取...")
                        if check_and_claim_erc20_balance(account_l1, ADDR_L1_ERC20, ERC20_AMOUNT, "L1 ERC-20"):
                            l1_token_balance, _ = get_erc20_balance(account_l1, ADDR_L1_ERC20)
                    
                    if l1_token_balance > 0:
                        # 使用实际余额进行桥接
                        bridge_amount = min(l1_token_balance, ERC20_AMOUNT)
                        deposit_erc20_to_l2(account_l1, account_l2, ADDR_L1_ERC20, ADDR_L2_ERC20, bridge_amount)
                    else:
                        print_warning("无法获取L1 ERC-20代币，跳过此任务")
                        continue
                        
                elif task_type == "withdraw_eth" and l2_balance >= Web3.to_wei("0.001", "ether"):
                    withdraw_eth_to_l1_via_message_passer(account_l2, account_l1, WITHDRAW_ETH_AMOUNT)
                    
                elif task_type == "withdraw_erc20" and l2_balance >= Web3.to_wei("0.001", "ether"):
                    # 检查L2 ERC-20代币余额
                    l2_token_balance, _ = get_erc20_balance(account_l2, ADDR_L2_ERC20)
                    if l2_token_balance > 0:
                        # 使用实际余额进行提现
                        withdraw_amount = min(l2_token_balance, ERC20_AMOUNT)
                        withdraw_erc20_to_l1(account_l2, account_l1, ADDR_L2_ERC20, withdraw_amount)
                    else:
                        print_warning("L2 ERC-20代币余额为零，跳过此任务")
                        print_info("提示: 请先执行 Sepolia ERC-20 → Giwa ERC-20 桥接")
                        continue
                        
                elif task_type == "self_transfer" and l2_balance >= Web3.to_wei("0.001", "ether"):
                    l2_self_transfer_eth(account_l2, amount_wei=Web3.to_wei("0.00005","ether"))
                else:
                    print_warning("跳过任务（余额不足或条件不满足）")
                    continue
                
                account_success += 1
                success_count += 1
                print_success(f"任务完成")
                
                # 任务间短暂暂停
                time.sleep(random.randint(3, 8))
                
            except Exception as e:
                print_error(f"任务失败: {e}")
                time.sleep(2)  # 失败后短暂暂停
        
        print_step("RESULT", f"账户 {format_address(account_address)}: {account_success}/{total_tasks_per_account} 任务成功")
        
        if account_success == 0:
            failed_accounts.append((account_address, "所有任务失败"))
        
        # 账户间暂停
        if account_idx < total_accounts:
            print_info(f"等待 10-30 秒后测试下一个账户...")
            time.sleep(random.randint(10, 30))
    
    # 执行全局任务（使用第一个账户）
    print(f"\n{Fore.MAGENTA}{'='*70}")
    print(f"🌍 执行全局任务")
    print(f"{'='*70}{Style.RESET_ALL}")
    
    for task_name, task_type in global_tasks:
        current_op += 1
        print_progress_bar(current_op-1, total_operations, f"全局任务: {task_name}")
        
        print(f"\n{Fore.CYAN}▶ {task_name}{Style.RESET_ALL}")
        
        try:
            if task_type == "deploy_contracts":
                # 使用第一个账户执行，无论余额
                deploy_account = Chain(
                    name=l2.name, rpc=l2.rpc, w3=l2.w3, account=all_accounts[0],
                    nonce=l2.w3.eth.get_transaction_count(all_accounts[0].address, "pending")
                )
                l2_multi_deploy_test(deploy_account)
                success_count += 1
            
        except Exception as e:
            print_error(f"全局任务失败: {e}")
    
    print_progress_bar(total_operations, total_operations, "全部完成")
    
    # 显示最终统计
    print_section_header("📊 循环执行结果")
    print_step("SUCCESS", f"成功操作: {success_count}/{total_operations}")
    print_step("ACCOUNTS", f"测试账户: {total_accounts} 个")
    
    if failed_accounts:
        print_step("FAILED", f"失败账户: {len(failed_accounts)} 个")
        for addr, reason in failed_accounts:
            print(f"  • {format_address(addr)}: {reason}")
    
    success_rate = (success_count / total_operations) * 100 if total_operations > 0 else 0
    if success_rate >= 80:
        print(f"{Fore.GREEN}🎉 优秀! 成功率: {success_rate:.1f}%{Style.RESET_ALL}")
    elif success_rate >= 60:
        print(f"{Fore.YELLOW}👍 良好! 成功率: {success_rate:.1f}%{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}🔧 需要优化! 成功率: {success_rate:.1f}%{Style.RESET_ALL}")

def countdown_24_hours():
    """24小时倒计时"""
    total_seconds = 24 * 60 * 60  # 24小时
    
    try:
        for remaining in range(total_seconds, 0, -1):
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            seconds = remaining % 60
            
            countdown_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            print(f"\r{Fore.BLUE}⏰ 距离下次循环: {countdown_str} (按 Ctrl+C 退出){Style.RESET_ALL}", end="", flush=True)
            time.sleep(1)
            
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}倒计时被中断{Style.RESET_ALL}")
        raise
    
    print(f"\n{Fore.GREEN}⏰ 24小时等待完成，开始下一轮循环{Style.RESET_ALL}")

# ========================
# 美化菜单
# ========================

def print_account_info(l1: Chain, l2: Chain):
    """显示账户信息"""
    l1_balance = l1.w3.eth.get_balance(l1.account.address)
    l2_balance = l2.w3.eth.get_balance(l2.account.address)
    
    print(f"{Fore.CYAN}{'═'*80}")
    print(f"📊 账户信息")
    print(f"{'═'*80}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}地址:{Style.RESET_ALL} {l1.account.address}")
    print(f"{Fore.BLUE}Sepolia ETH:{Style.RESET_ALL} {format_eth(l1_balance)}")
    print(f"{Fore.GREEN}GIWA ETH:{Style.RESET_ALL} {format_eth(l2_balance)}")
    print(f"{Fore.CYAN}{'═'*80}{Style.RESET_ALL}")

def print_main_menu():
    """显示主菜单"""
    menu_items = [
        ("1", "🎯 批量分发+桥接", "从首个账户分发0.1ETH并桥接0.05ETH到所有目标地址"),
        ("2", "🪙 领取测试代币", "从L1/L2水龙头领取ERC-20测试代币 (支持批量)"),
        ("3", "🪙 ERC-20桥接(L1→L2)", "Sepolia ERC-20→Giwa ERC-20(自动检查余额和领取)"),
        ("4", "💰 ETH桥接(L2→L1)", "Giwa ETH→Sepolia ETH"),
        ("5", "🔄 ERC-20桥接(L2→L1)", "Giwa ERC-20→Sepolia ERC-20(智能余额检测+自动领取)"),
        ("6", "🔁 L2 ETH自转测试", "在GIWA网络内进行ETH转账测试"),
        ("7", "🚀 智能合约部署", "在GIWA网络部署多种类型合约"),
        ("8", "🎲 多账户循环测试", "所有地址循环测试，可选24小时定时执行"),
        ("0", "🚪 退出程序", "安全退出测试程序")
    ]
    
    print(f"\n{Fore.CYAN}{'╔'+'═'*70+'╗'}")
    print(f"║{' '*25}🌉 GIWA 测试菜单{' '*25}║")
    print(f"{'╠'+'═'*70+'╣'}{Style.RESET_ALL}")
    
    for key, title, desc in menu_items:
        # 调整列宽以适应更长的描述
        title_part = f" {Fore.WHITE}[{key}]{Style.RESET_ALL} {title:<22}"
        desc_part = f"{Fore.CYAN}{desc}{Style.RESET_ALL}"
        print(f"║{title_part}│ {desc_part}")
    
    print(f"{Fore.CYAN}{'╚'+'═'*70+'╝'}{Style.RESET_ALL}")

def get_user_choice() -> str:
    """获取用户选择"""
    try:
        choice = input(f"\n{Fore.YELLOW}请选择操作 (0-8): {Style.RESET_ALL}").strip()
        return choice
    except (EOFError, KeyboardInterrupt):
        print(f"\n{Fore.YELLOW}用户中断，程序退出{Style.RESET_ALL}")
        return "0"

def pause_and_continue():
    """暂停并等待用户继续"""
    try:
        input(f"\n{Fore.BLUE}按 Enter 键返回主菜单...{Style.RESET_ALL}")
    except (EOFError, KeyboardInterrupt):
        pass

# ========================
# 主程序
# ========================

def main():
    """主程序入口"""
    try:
        # 检查命令行参数
        import sys
        auto_start_cycle = "--auto-start-cycle" in sys.argv
        
        # 显示启动横幅
        print_banner()
        
        # 显示网络信息
        print_section_header("🌐 网络配置")
        print_step("L1", f"Sepolia RPC: {L1_RPC_DEFAULT}")
        print_step("L2", f"GIWA RPC: {L2_RPC_DEFAULT}")
        
        # 加载账户
        print_section_header("🔑 加载账户")
        acct_first = load_first_private_key()
        accounts_all = load_all_accounts()
        
        # 连接网络
        print_section_header("🔗 连接网络")
        w3_l1 = make_w3(L1_RPC_DEFAULT)
        w3_l2 = make_w3(L2_RPC_DEFAULT)
        
        # 获取 nonce
        nonce_l1 = w3_l1.eth.get_transaction_count(acct_first.address, "pending")
        nonce_l2 = w3_l2.eth.get_transaction_count(acct_first.address, "pending")
        
        # 创建链对象
        l1 = Chain(name="Ethereum Sepolia", rpc=L1_RPC_DEFAULT, w3=w3_l1, account=acct_first, nonce=nonce_l1)
        l2 = Chain(name="GIWA Sepolia", rpc=L2_RPC_DEFAULT, w3=w3_l2, account=acct_first, nonce=nonce_l2)
        
        print_success("所有初始化完成")
        
        # 如果是自动启动模式，直接进入24小时循环
        if auto_start_cycle:
            print_success("自动启动24小时循环模式")
            print_warning("这是服务模式，按 Ctrl+C 可以安全退出")
            
            # 模拟选择24小时循环
            import io, contextlib
            
            # 重定向输入以自动选择 'y'
            old_stdin = sys.stdin
            sys.stdin = io.StringIO('y\n')
            
            try:
                one_click_flow_random(l1, l2, accounts_all)
            finally:
                sys.stdin = old_stdin
            
            return
        
        # 正常交互模式
        print_success("进入交互模式")
        
        # 主循环
        while True:
            print_account_info(l1, l2)
            print_main_menu()
            choice = get_user_choice()
            
            try:
                if choice == "1":
                    distribute_and_bridge(l1, l2, accounts_all)
                elif choice == "2":
                    claim_test_tokens_menu(l1, l2, accounts_all)
                elif choice == "3":
                    deposit_erc20_to_l2(l1, l2, ADDR_L1_ERC20, ADDR_L2_ERC20, ERC20_AMOUNT)
                elif choice == "4":
                    withdraw_eth_to_l1_via_message_passer(l2, l1, WITHDRAW_ETH_AMOUNT)
                elif choice == "5":
                    withdraw_erc20_to_l1(l2, l1, ADDR_L2_ERC20, ERC20_AMOUNT)
                elif choice == "6":
                    l2_self_transfer_eth(l2, amount_wei=Web3.to_wei("0.00005","ether"))
                elif choice == "7":
                    l2_multi_deploy_test(l2)
                elif choice == "8":
                    one_click_flow_random(l1, l2, accounts_all)
                elif choice == "0":
                    print(f"{Fore.GREEN}感谢使用 GIWA 测试工具! 再见! 👋{Style.RESET_ALL}")
                    break
                else:
                    print_error("无效选项，请重新选择")
                    continue
                    
                pause_and_continue()
                
            except KeyboardInterrupt:
                print_warning("\n操作被用户中断")
                pause_and_continue()
            except Exception as e:
                print_error(f"执行出错: {e}")
                pause_and_continue()
                
    except Exception as e:
        print_error(f"程序初始化失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
