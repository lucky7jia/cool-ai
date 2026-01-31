"""Stock data plugin - fetches real-time stock data from Tencent Finance API"""

import re
from typing import Any, Optional
import httpx


class StockDataPlugin:
    """Plugin for fetching real-time stock data"""
    
    name = "stock_data"
    description = "获取实时股票数据"
    
    # 股票代码映射 (名称 -> 代码)
    STOCK_ALIASES = {
        "spacex": "us.RKLB",  # Rocket Lab (SpaceX 概念股)
        "tesla": "us.TSLA",
        "特斯拉": "us.TSLA",
        "腾讯": "hk00700",
        "阿里巴巴": "hk09988",
        "茅台": "sh600519",
        "贵州茅台": "sh600519",
        "中国平安": "sh601318",
        "招商银行": "sh600036",
        "宁德时代": "sz300750",
    }
    
    async def initialize(self, config: dict[str, Any]) -> None:
        """Initialize the plugin"""
        pass
    
    def _parse_stock_code(self, query: str) -> Optional[str]:
        """Parse stock code from query"""
        query_lower = query.lower()
        
        # Check aliases
        for name, code in self.STOCK_ALIASES.items():
            if name in query:
                return code
        
        # Check for direct code patterns
        # A股: sh600xxx, sz000xxx, sz002xxx, sz300xxx
        # 港股: hk0xxxx
        patterns = [
            r'(sh[0-9]{6})',
            r'(sz[0-9]{6})',
            r'(hk[0-9]{5})',
            r'([0-9]{5,6})',  # 纯数字
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query_lower)
            if match:
                code = match.group(1)
                # 补全前缀
                if code.isdigit():
                    if len(code) == 5:
                        code = f"hk{code}"
                    elif code.startswith('6'):
                        code = f"sh{code}"
                    elif code.startswith('0') or code.startswith('3'):
                        code = f"sz{code}"
                return code
        
        return None
    
    async def get_stock_data(self, query: str) -> Optional[dict[str, Any]]:
        """
        Get real-time stock data.
        
        Args:
            query: Stock name or code
        
        Returns:
            Dict with stock data or None if not found
        """
        code = self._parse_stock_code(query)
        if not code:
            return None
        
        try:
            # Use Tencent Finance API
            if code.startswith('hk'):
                url = f"https://qt.gtimg.cn/q=r_{code}"
            else:
                url = f"https://qt.gtimg.cn/q={code}"
            
            async with httpx.AsyncClient(verify=False, timeout=10) as client:
                resp = await client.get(url)
                data = resp.text
            
            return self._parse_tencent_data(code, data)
        
        except Exception as e:
            print(f"获取股票数据失败: {e}")
            return None
    
    def _parse_tencent_data(self, code: str, raw_data: str) -> Optional[dict[str, Any]]:
        """Parse Tencent Finance API response"""
        try:
            # Extract data between quotes
            match = re.search(r'"([^"]+)"', raw_data)
            if not match:
                return None
            
            fields = match.group(1).split('~')
            if len(fields) < 50:
                return None
            
            # Field mapping (Tencent format)
            is_hk = code.startswith('hk')
            
            if is_hk:
                # 港股字段映射:
                # 1=名称, 2=代码, 3=现价, 4=昨收, 5=今开
                # 30=时间, 31=涨跌额, 32=涨跌幅, 33=最高, 34=最低
                # 36=成交量, 37=成交额, 39=PE, 43=52周高, 44=52周低
                # 45=市值(亿), 48=年初至今涨幅
                def safe_float(s):
                    try:
                        return float(s) if s and s.replace('.','').replace('-','').isdigit() else 0
                    except:
                        return 0
                
                return {
                    "code": code,
                    "name": fields[1],
                    "price": safe_float(fields[3]),
                    "change": safe_float(fields[31]),
                    "change_pct": safe_float(fields[32]),
                    "open": safe_float(fields[5]),
                    "high": safe_float(fields[33]),
                    "low": safe_float(fields[34]),
                    "volume": safe_float(fields[36]),
                    "amount": safe_float(fields[37]),
                    "pe": safe_float(fields[39]),
                    "pb": 0,  # 港股数据中没有PB
                    "market_cap": safe_float(fields[45]),
                    "time": fields[30],
                    "currency": "HKD",
                    "market": "港股",
                }
            else:
                return {
                    "code": code,
                    "name": fields[1],
                    "price": float(fields[3]) if fields[3] else 0,
                    "change": float(fields[31]) if fields[31] else 0,
                    "change_pct": float(fields[32]) if fields[32] else 0,
                    "open": float(fields[5]) if fields[5] else 0,
                    "high": float(fields[33]) if fields[33] else 0,
                    "low": float(fields[34]) if fields[34] else 0,
                    "volume": float(fields[36]) if fields[36] else 0,
                    "amount": float(fields[37]) if fields[37] else 0,
                    "pe": float(fields[39]) if fields[39] else 0,
                    "pb": float(fields[46]) if fields[46] else 0,
                    "market_cap": float(fields[45]) if fields[45] else 0,
                    "time": fields[30],
                    "currency": "CNY",
                    "market": "A股",
                }
        except Exception as e:
            print(f"解析股票数据失败: {e}")
            return None
    
    def format_stock_info(self, data: dict[str, Any]) -> str:
        """Format stock data as readable text"""
        if not data:
            return "未找到股票数据"
        
        return f"""### 📊 {data['name']} ({data['code']}) 实时行情

| 指标 | 数值 |
|------|------|
| **最新价** | {data['price']:.3f} {data['currency']} |
| **涨跌幅** | {data['change_pct']:+.2f}% ({data['change']:+.3f}) |
| **今开** | {data['open']:.3f} |
| **最高** | {data['high']:.3f} |
| **最低** | {data['low']:.3f} |
| **成交量** | {data['volume']/10000:.2f} 万股 |
| **成交额** | {data['amount']/100000000:.2f} 亿 |
| **市盈率** | {data['pe']:.2f} |
| **市净率** | {data['pb']:.2f} |
| **市值** | {data['market_cap']:.2f} 亿 |
| **市场** | {data['market']} |
| **更新时间** | {data['time']} |
"""


# Global instance
_stock_plugin: Optional[StockDataPlugin] = None


def get_stock_plugin() -> StockDataPlugin:
    """Get global stock plugin instance"""
    global _stock_plugin
    if _stock_plugin is None:
        _stock_plugin = StockDataPlugin()
    return _stock_plugin


async def get_stock_context(query: str) -> str:
    """
    Get stock data context for a query.
    
    This is a helper function to be called before analysis.
    """
    plugin = get_stock_plugin()
    data = await plugin.get_stock_data(query)
    if data:
        return plugin.format_stock_info(data)
    return ""
