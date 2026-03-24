"""
Akshare 数据提供者
基于原项目逻辑，但使用腾讯接口解决连接问题
"""
import logging
import time
import traceback
from datetime import datetime, timedelta
from typing import List
import pandas as pd
from dateutil.parser import parser
from tqdm import tqdm
import akshare as ak


class Akshare:
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(Akshare, cls).__new__(cls)
        return cls._instance

    def __init__(self, **kwargs):
        if not self._initialized:
            self.time_interval = kwargs.get("time_interval", "daily")
            self.data_source = kwargs.get("data_source", None)
            self.start_date = kwargs.get("start_date", None)
            self.end_date = kwargs.get("end_date", None)

            if "adj" in kwargs.keys():
                self.adj = kwargs["adj"]
                print(f"Using {self.adj} method.")
            else:
                self.adj = ""

            if "period" in kwargs.keys():
                self.period = kwargs["period"]
            else:
                self.period = "daily"

            Akshare._initialized = True

    def get_stock_dataframe(self, stock_code: str, se: str = None, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        获取股票历史K线数据，返回与数据库格式兼容的DataFrame
        基于原项目逻辑，使用腾讯接口

        Args:
            stock_code: 股票代码（如：000001）
            se: 交易所代码（sh/sz），如果不提供则自动判断
            start_date: 开始日期（YYYY-MM-DD格式）
            end_date: 结束日期（YYYY-MM-DD格式）

        Returns:
            DataFrame: 包含以下列的股票数据：
                - date: 交易日期 (datetime类型)
                - open: 开盘价
                - high: 最高价
                - low: 最低价
                - close: 收盘价
                - volume: 成交量
                - turnover: 成交额
                - turnover_rate: 换手率
                - shake_rate: 振幅
                - change_rate: 涨跌幅
                - change_amount: 涨跌额
        """
        # 自动判断交易所
        if se is None:
            if stock_code.startswith('6'):
                se = 'sh'  # 上海证券交易所
            elif stock_code.startswith(('0', '3')):
                se = 'sz'  # 深圳证券交易所
            elif stock_code.startswith('8'):
                se = 'bj'  # 北京证券交易所
            else:
                se = 'sz'  # 默认深圳

        # 设置默认日期范围（默认获取最近3年数据）
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365*3)).strftime('%Y-%m-%d')

        try:
            # 使用腾讯接口（解决连接问题）
            tx_symbol = f"{se.lower()}{stock_code}"
            tx_start = start_date.replace('-', '')
            tx_end = end_date.replace('-', '')

            df = ak.stock_zh_a_hist_tx(
                symbol=tx_symbol,
                start_date=tx_start,
                end_date=tx_end,
                adjust='qfq'
            )

            if df is None or df.empty:
                print(f"⚠️ 未获取到股票数据: {stock_code}")
                empty_df = pd.DataFrame(columns=[
                    'date', 'open', 'high', 'low', 'close', 'volume',
                    'turnover', 'turnover_rate', 'shake_rate',
                    'change_rate', 'change_amount'
                ])
                empty_df['date'] = pd.to_datetime(empty_df['date'])
                return empty_df

            # 腾讯接口返回的列：['date', 'open', 'close', 'high', 'low', 'amount']
            # 转换为数据库格式

            # 转换日期格式
            df['date'] = pd.to_datetime(df['date'])

            # 重命名 amount 为 turnover
            df = df.rename(columns={'amount': 'turnover'})

            # 按日期排序以确保计算正确
            df = df.sort_values('date').reset_index(drop=True)

            # 计算缺失的列（基于原项目逻辑）
            df['prev_close'] = df['close'].shift(1)
            df['change_rate'] = ((df['close'] - df['prev_close']) / df['prev_close'] * 100).round(2)
            df['change_amount'] = (df['close'] - df['prev_close']).round(2)
            df['shake_rate'] = ((df['high'] - df['low']) / df['prev_close'] * 100).round(2)

            # 第一行设为0
            df.loc[0, 'change_rate'] = 0
            df.loc[0, 'change_amount'] = 0
            df.loc[0, 'shake_rate'] = 0
            df = df.drop(columns=['prev_close'])

            # 腾讯接口的 turnover 是成交额，volume 设为0（不提供）
            df['volume'] = 0
            df['turnover_rate'] = 0

            # 确保数值类型正确
            for col in ['open', 'high', 'low', 'close', 'turnover', 'volume',
                       'turnover_rate', 'shake_rate', 'change_rate', 'change_amount']:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            # 选择需要的列
            columns_to_keep = [
                'date', 'open', 'high', 'low', 'close', 'volume',
                'turnover', 'turnover_rate', 'shake_rate',
                'change_rate', 'change_amount'
            ]

            result_df = df[columns_to_keep].copy()

            print(f"✅ 成功获取 {stock_code} 数据，共 {len(result_df)} 条记录")
            return result_df

        except Exception as e:
            print(f"❌ 获取股票 {stock_code} 数据失败: {e}")
            traceback.print_exc()
            # 返回正确的空DataFrame结构
            empty_df = pd.DataFrame(columns=[
                'date', 'open', 'high', 'low', 'close', 'volume',
                'turnover', 'turnover_rate', 'shake_rate',
                'change_rate', 'change_amount'
            ])
            empty_df['date'] = pd.to_datetime(empty_df['date'])
            return empty_df

    def update_all_stocks_list(self, db):
        """
        使用 Akshare API 更新所有股票列表到数据库
        基于原项目逻辑
        """
        from db.models import Stock

        print("Start updating all stocks list!")
        try:
            # 获取所有股票列表
            stock_list = ak.stock_info_a_code_name()

            if stock_list is None or stock_list.empty:
                print("⚠️ 未获取到股票列表")
                return

            print(f"📊 获取到 {len(stock_list)} 只股票")

            # 遍历股票列表，更新到数据库
            for _, each_stock in stock_list.iterrows():
                stock_code = each_stock.get('code')  # 如: 000001
                name = each_stock.get('name')

                # 根据代码推断交易所
                if stock_code.startswith('6'):
                    se = 'sh'  # 上海证券交易所
                elif stock_code.startswith(('0', '3')):
                    se = 'sz'  # 深圳证券交易所
                elif stock_code.startswith('8'):
                    se = 'bj'  # 北京证券交易所
                else:
                    se = 'unknown'

                # 检查数据库中是否已存在该股票
                record = db.session.query(Stock).filter(Stock.code == stock_code).scalar()

                if record:
                    # 记录存在，更新名称和交易所
                    if record.name != name:
                        old_name = record.name
                        record.name = name
                        print("Updated stock: {} {} with new name: {}".format(stock_code, old_name, name))
                    if record.se != se:
                        old_se = record.se
                        record.se = se
                        print("Updated stock: {} {} {} with new se: {}".format(stock_code, record.name, old_se, se))
                else:
                    # 记录不存在，添加新记录
                    new_record = Stock(
                        code=stock_code,
                        name=name,
                        se=se,
                        type='s',
                    )
                    db.session.add(new_record)
                    print("Added new stock: {} {}".format(stock_code, name))

                db.session.commit()

            print("Finished update all stocks list!")
            print(datetime.now())

        except Exception as e:
            err = traceback.format_exc()
            logging.error(f"Error updating stocks list: {err}")
            db.session.rollback()
            raise e
        return
