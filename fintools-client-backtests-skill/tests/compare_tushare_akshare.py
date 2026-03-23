"""
测试脚本：对比 Tushare 和 Akshare 的股票数据是否一致
"""
import os
import sys
import pandas as pd

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

def compare_stock_data(stock_code: str = '000001'):
    """对比 Tushare 和 Akshare 的股票数据"""

    print(f"\n{'='*60}")
    print(f"测试股票代码: {stock_code}")
    print(f"{'='*60}\n")

    # 获取 Tushare 数据
    print("正在获取 Tushare 数据...")
    try:
        from data_processing.data_provider.tushare import Tushare
        ts_client = Tushare()

        # 自动判断交易所
        se = None
        if stock_code.startswith('6'):
            se = 'sh'
        elif stock_code.startswith(('0', '3')):
            se = 'sz'
        elif stock_code.startswith('8'):
            se = 'bj'
        else:
            se = 'sz'

        ts_data = ts_client.get_stock_dataframe(stock_code, se)

        if ts_data is not None and not ts_data.empty:
            print(f"✅ Tushare 数据获取成功，共 {len(ts_data)} 条记录")
            print(f"   日期范围: {ts_data['date'].min()} 至 {ts_data['date'].max()}")
            print(f"   列: {list(ts_data.columns)}")
        else:
            print(f"❌ Tushare 数据获取失败或为空")
            return False

    except Exception as e:
        print(f"❌ Tushare 获取数据失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 获取 Akshare 数据
    print("\n正在获取 Akshare 数据...")
    try:
        from data_processing.data_provider.akshare import Akshare
        ak_client = Akshare()

        ak_data = ak_client.get_stock_dataframe(stock_code)

        if ak_data is not None and not ak_data.empty:
            print(f"✅ Akshare 数据获取成功，共 {len(ak_data)} 条记录")
            print(f"   日期范围: {ak_data['date'].min()} 至 {ak_data['date'].max()}")
            print(f"   列: {list(ak_data.columns)}")
        else:
            print(f"❌ Akshare 数据获取失败或为空")
            return False

    except Exception as e:
        print(f"❌ Akshare 获取数据失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 对比数据
    print(f"\n{'='*60}")
    print("数据对比结果")
    print(f"{'='*60}\n")

    # 1. 对比记录数量
    print(f"1. 记录数量对比:")
    print(f"   Tushare: {len(ts_data)} 条")
    print(f"   Akshare: {len(ak_data)} 条")
    if len(ts_data) == len(ak_data):
        print(f"   ✅ 数量一致")
    else:
        print(f"   ❌ 数量不一致")

    # 2. 对比列
    print(f"\n2. 列对比:")
    ts_cols = set(ts_data.columns)
    ak_cols = set(ak_data.columns)
    if ts_cols == ak_cols:
        print(f"   ✅ 列一致")
    else:
        print(f"   ❌ 列不一致")
        print(f"   Tushare 独有列: {ts_cols - ak_cols}")
        print(f"   Akshare 独有列: {ak_cols - ts_cols}")

    # 3. 对比日期范围
    print(f"\n3. 日期范围对比:")
    print(f"   Tushare: {ts_data['date'].min()} 至 {ts_data['date'].max()}")
    print(f"   Akshare: {ak_data['date'].min()} 至 {ak_data['date'].max()}")

    # 4. 对比最近几天的数据
    print(f"\n4. 最近5天数据对比:")
    ts_tail = ts_data.tail(5).copy()
    ak_tail = ak_data.tail(5).copy()

    # 将日期格式化为字符串方便对比
    ts_tail['date_str'] = ts_tail['date'].dt.strftime('%Y-%m-%d')
    ak_tail['date_str'] = ak_tail['date'].dt.strftime('%Y-%m-%d')

    print(f"\n   Tushare 最近5天:")
    print(ts_tail[['date_str', 'open', 'high', 'low', 'close', 'volume']].to_string(index=False))

    print(f"\n   Akshare 最近5天:")
    print(ak_tail[['date_str', 'open', 'high', 'low', 'close', 'volume']].to_string(index=False))

    # 5. 详细对比（如果有相同的日期）
    print(f"\n5. 详细对比（相同日期的数据）:")
    common_dates = set(ts_tail['date_str']) & set(ak_tail['date_str'])
    if common_dates:
        for date_str in sorted(common_dates):
            ts_row = ts_tail[ts_tail['date_str'] == date_str].iloc[0]
            ak_row = ak_tail[ak_tail['date_str'] == date_str].iloc[0]

            print(f"\n   日期: {date_str}")
            print(f"   {'字段':<12} {'Tushare':<15} {'Akshare':<15} {'差异':<10}")
            print(f"   {'-'*60}")

            for col in ['open', 'high', 'low', 'close', 'volume']:
                ts_val = ts_row[col]
                ak_val = ak_row[col]
                diff = abs(ts_val - ak_val) if pd.notna(ts_val) and pd.notna(ak_val) else None

                if pd.notna(diff) and diff > 0:
                    diff_str = f"{diff:.2f}"
                    if diff > 1:
                        diff_str += " ❌"
                    else:
                        diff_str += " ⚠️"
                else:
                    diff_str = "✅"

                print(f"   {col:<12} {ts_val:<15.2f} {ak_val:<15.2f} {diff_str:<10}")
    else:
        print("   ⚠️ 没有相同的日期可以对比")

    # 6. 结论
    print(f"\n{'='*60}")
    print("结论")
    print(f"{'='*60}")

    # 简单的统计对比
    if len(ts_data) == len(ak_data) and ts_cols == ak_cols:
        print("✅ 数据结构和数量一致")
        print("✅ 可以考虑切换到 Akshare（免费，无需API Key）")
        return True
    else:
        print("❌ 数据结构或数量不一致")
        print("⚠️ 需要进一步调查差异原因")
        return False

def main():
    """主函数"""
    print("开始对比 Tushare 和 Akshare 的股票数据...\n")

    # 测试几个不同类型的股票
    test_stocks = [
        '000001',  # 平安银行（深圳主板）
        '600000',  # 浦发银行（上海主板）
        '300750',  # 宁德时代（创业板）
    ]

    results = {}
    for stock_code in test_stocks:
        try:
            result = compare_stock_data(stock_code)
            results[stock_code] = result
        except Exception as e:
            print(f"\n❌ 测试股票 {stock_code} 时出错: {e}")
            import traceback
            traceback.print_exc()
            results[stock_code] = False

    # 最终总结
    print(f"\n{'='*60}")
    print("最终总结")
    print(f"{'='*60}\n")

    for stock_code, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{stock_code}: {status}")

    all_passed = all(results.values())
    if all_passed:
        print(f"\n✅ 所有测试通过！")
        print(f"✅ 建议：可以将数据源切换到 Akshare（免费，无需API Key）")
    else:
        print(f"\n❌ 部分测试失败")
        print(f"⚠️ 建议：需要进一步调查差异原因")

if __name__ == '__main__':
    main()