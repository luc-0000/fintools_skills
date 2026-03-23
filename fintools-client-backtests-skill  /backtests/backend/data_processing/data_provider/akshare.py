"""
Akshare 数据提供者 - 简化版，用于替代 Tushare
只保留 simulator 运行所需的核心方法
"""
import pandas as pd
from datetime import datetime, timedelta
import akshare as ak


class Akshare:
    """
    Akshare 数据提供者类

    提供股票历史数据获取功能，与 Tushare API 兼容
    Akshare 是免费的开源金融数据接口，无需 API Key
    """
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(Akshare, cls).__new__(cls)
        return cls._instance

    def __init__(self, **kwargs):
        if not self._initialized:
            self.time_interval = kwargs.get("time_interval", "daily")
            self.adj = kwargs.get("adj", "")
            Akshare._initialized = True

    def get_stock_dataframe(self, stock_code: str, se: str = None, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        获取股票历史K线数据，返回与数据库格式兼容的DataFrame
        兼容 Tushare 的 get_stock_dataframe 方法

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
        # 自动判断交易所（如果未提供）
        # 注意：Akshare 的 stock_zh_a_hist 只需要纯数字代码，不需要交易所后缀
        # 所以这里的 se 参数实际上不被使用，但保留以兼容接口
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
            # 获取日线数据（使用前复权）
            df = ak.stock_zh_a_hist(
                symbol=stock_code,
                period='daily',
                start_date=start_date,
                end_date=end_date,
                adjust='qfq'  # 前复权
            )

            if df is None or df.empty:
                print(f"⚠️ 未获取到股票数据: {stock_code}")
                return pd.DataFrame()

            # 重命名列以匹配数据库格式
            df = df.rename(columns={
                '日期': 'date',
                '开盘': 'open',
                '最高': 'high',
                '最低': 'low',
                '收盘': 'close',
                '成交量': 'volume',
                '成交额': 'turnover',
                '振幅': 'shake_rate',
                '涨跌幅': 'change_rate',
                '涨跌额': 'change_amount',
                '换手率': 'turnover_rate'
            })

            # 转换日期格式为datetime（重要：后续计算需要对比datetime）
            df['date'] = pd.to_datetime(df['date'])

            # 确保振幅和涨跌幅是数值类型
            df['shake_rate'] = pd.to_numeric(df['shake_rate'], errors='coerce')
            df['change_rate'] = pd.to_numeric(df['change_rate'], errors='coerce')
            df['change_amount'] = pd.to_numeric(df['change_amount'], errors='coerce')

            # 选择需要的列（与数据库格式一致）
            columns_to_keep = [
                'date', 'open', 'high', 'low', 'close', 'volume',
                'turnover', 'turnover_rate', 'shake_rate',
                'change_rate', 'change_amount'
            ]

            result_df = df[columns_to_keep].copy()

            # 按日期排序
            result_df = result_df.sort_values('date').reset_index(drop=True)

            print(f"✅ 成功获取 {stock_code} 数据，共 {len(result_df)} 条记录")
            return result_df

        except Exception as e:
            print(f"❌ 获取股票 {stock_code} 数据失败: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()

    def update_all_stocks_list(self, db):
        """
        使用 Akshare API 更新所有股票列表到数据库
        功能与 Tushare 的 update_all_stocks_list 相同
        """
        from db.models import Stock
        from datetime import datetime

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
            import traceback
            err = traceback.format_exc()
            print(f"❌ Error updating stocks list: {err}")
            db.session.rollback()
            raise e
        return
