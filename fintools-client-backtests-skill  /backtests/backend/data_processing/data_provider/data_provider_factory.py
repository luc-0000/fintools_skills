"""
数据提供者工厂 - 统一管理 Tushare 和 Akshare 的切换
"""
import os
from typing import Optional


class DataProviderConfig:
    """数据提供者配置"""
    _provider: Optional[str] = None

    @classmethod
    def get_provider(cls) -> str:
        """获取当前数据提供者"""
        if cls._provider is None:
            # 优先从环境变量读取
            cls._provider = os.getenv('DATA_PROVIDER', 'akshare').lower()
        return cls._provider

    @classmethod
    def set_provider(cls, provider: str):
        """设置数据提供者"""
        provider = provider.lower()
        if provider not in ['tushare', 'akshare']:
            raise ValueError(f"Invalid provider: {provider}. Must be 'tushare' or 'akshare'")
        cls._provider = provider
        print(f"✅ 数据源已切换为: {provider}")

    @classmethod
    def reset(cls):
        """重置为默认（akshare）"""
        cls._provider = None


def get_data_tool():
    """
    获取当前配置的数据提供者实例

    Returns:
        Tushare 或 Akshare 实例
    """
    provider = DataProviderConfig.get_provider()

    if provider == 'tushare':
        from .tushare import Tushare
        print("📊 使用数据源: Tushare")
        return Tushare()
    elif provider == 'akshare':
        from .akshare import Akshare
        print("📊 使用数据源: Akshare")
        return Akshare()
    else:
        raise ValueError(f"Unknown data provider: {provider}")


# 默认使用 Akshare
DataProviderConfig.set_provider('akshare')
