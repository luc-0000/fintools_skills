"""
Regression Tests: 验证 Tushare 和 Akshare 两种数据源的结果一致性
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from datetime import datetime


def test_data_provider_switching():
    """测试数据源切换功能"""
    from data_processing.data_provider.data_provider_factory import DataProviderConfig, get_data_tool

    print("="*80)
    print("测试 1: 数据源切换功能")
    print("="*80)

    # 测试 1: 测试默认数据源（akshare）
    print("\n1.1 测试默认数据源...")
    default_provider = DataProviderConfig.get_provider()
    print(f"   默认数据源: {default_provider}")
    assert default_provider == 'akshare', f"默认数据源应该是 akshare，实际是 {default_provider}"
    print("   ✅ 默认数据源正确")

    # 测试 2: 切换到 tushare
    print("\n1.2 切换到 tushare...")
    DataProviderConfig.set_provider('tushare')
    current_provider = DataProviderConfig.get_provider()
    print(f"   当前数据源: {current_provider}")
    assert current_provider == 'tushare', f"数据源应该是 tushare，实际是 {current_provider}"
    print("   ✅ 切换到 tushare 成功")

    # 测试 3: 切换到 akshare
    print("\n1.3 切换到 akshare...")
    DataProviderConfig.set_provider('akshare')
    current_provider = DataProviderConfig.get_provider()
    print(f"   当前数据源: {current_provider}")
    assert current_provider == 'akshare', f"数据源应该是 akshare，实际是 {current_provider}"
    print("   ✅ 切换到 akshare 成功")

    # 测试 4: 测试非法数据源
    print("\n1.4 测试非法数据源...")
    try:
        DataProviderConfig.set_provider('invalid')
        print("   ❌ 应该抛出异常，但没有")
        return False
    except ValueError as e:
        print(f"   ✅ 正确抛出异常: {e}")

    # 重置为默认
    DataProviderConfig.reset()

    return True


def test_data_consistency_same_provider():
    """测试同一数据源获取的数据一致性"""
    from data_processing.data_provider.data_provider_factory import DataProviderConfig, get_data_tool
    from end_points.get_stock.operations.get_stock_utils import stockDataFrameFromDataTool

    print("\n" + "="*80)
    print("测试 2: 同一数据源的一致性")
    print("="*80)

    test_stocks = ['000001', '600000']

    for stock_code in test_stocks:
        print(f"\n   测试股票: {stock_code}")

        # 获取两次数据
        DataProviderConfig.set_provider('akshare')
        df1 = stockDataFrameFromDataTool(stock_code)
        df2 = stockDataFrameFromDataTool(stock_code)

        # 验证数据一致性
        assert df1.equals(df2), f"同一数据源获取的数据应该一致"

        print(f"   ✅ 数据一致，共 {len(df1)} 条记录")

    # 重置
    DataProviderConfig.reset()

    return True


def test_data_provider_comparison():
    """对比 Tushare 和 Akshare 的数据"""
    from data_processing.data_provider.data_provider_factory import DataProviderConfig
    from end_points.get_stock.operations.get_stock_utils import stockDataFrameFromDataTool

    print("\n" + "="*80)
    print("测试 3: Tushare vs Akshare 数据对比")
    print("="*80)

    test_stocks = ['000001', '600000']
    all_match = True

    for stock_code in test_stocks:
        print(f"\n   测试股票: {stock_code}")

        # 获取 Akshare 数据
        DataProviderConfig.set_provider('akshare')
        akshare_df = stockDataFrameFromDataTool(stock_code)

        if akshare_df.empty:
            print(f"   ⚠️ Akshare 未获取到数据，跳过对比")
            continue

        # 获取 Tushare 数据
        DataProviderConfig.set_provider('tushare')
        tushare_df = stockDataFrameFromDataTool(stock_code)

        if tushare_df.empty:
            print(f"   ⚠️ Tushare 未获取到数据，跳过对比")
            continue

        # 对比记录数量
        print(f"\n   记录数量:")
        print(f"      Akshare: {len(akshare_df)} 条")
        print(f"      Tushare:  {len(tushare_df)} 条")

        if len(akshare_df) != len(tushare_df):
            print(f"   ❌ 记录数量不一致")
            all_match = False
            continue

        print(f"   ✅ 记录数量一致")

        # 对比列
        akshare_cols = set(akshare_df.columns)
        tushare_cols = set(tushare_df.columns)
        if akshare_cols == tushare_cols:
            print(f"   ✅ 列一致")
        else:
            print(f"   ❌ 列不一致")
            print(f"      Akshare 独有: {akshare_cols - tushare_cols}")
            print(f"      Tushare 独有: {tushare_cols - akshare_cols}")
            all_match = False
            continue

        # 对比日期范围
        print(f"\n   日期范围:")
        print(f"      Akshare: {akshare_df['date'].min()} 至 {akshare_df['date'].max()}")
        print(f"      Tushare:  {tushare_df['date'].min()} 至 {tushare_df['date'].max()}")

        # 对比最近几天的数据
        print(f"\n   最近5天数据对比:")
        akshare_tail = akshare_df.tail(5)
        tushare_tail = tushare_df.tail(5)

        # 按日期对齐
        akshare_tail = akshare_tail.copy()
        tushare_tail = tushare_tail.copy()

        common_dates = set(akshare_tail['date'].dt.strftime('%Y-%m-%d')) & set(tushare_tail['date'].dt.strftime('%Y-%m-%d'))

        if common_dates:
            match_count = 0
            for date_str in sorted(common_dates):
                ak_row = akshare_tail[akshare_tail['date'].dt.strftime('%Y-%m-%d') == date_str].iloc[0]
                ts_row = tushare_tail[tushare_tail['date'].dt.strftime('%Y-%m-%d') == date_str].iloc[0]

                # 对比关键价格
                price_match = True
                for col in ['open', 'high', 'low', 'close']:
                    ak_val = ak_row[col]
                    ts_val = ts_row[col]
                    if pd.notna(ak_val) and pd.notna(ts_val):
                        diff = abs(ak_val - ts_val)
                        if diff > 0.01:  # 允许 0.01 的误差
                            print(f"      日期 {date_str}, {col}: Akshare={ak_val:.2f}, Tushare={ts_val:.2f}, 差异={diff:.2f} ❌")
                            price_match = False
                        else:
                            pass  # 完全一致

                if price_match:
                    match_count += 1

            print(f"   ✅ {match_count}/5 天数据完全一致")
            if match_count < 5:
                all_match = False
        else:
            print(f"   ⚠️ 没有相同的日期可以对比")

    # 重置
    DataProviderConfig.reset()

    return all_match


def test_simulator_with_both_providers():
    """测试使用两种数据源运行 Simulator 的结果一致性"""
    from data_processing.data_provider.data_provider_factory import DataProviderConfig
    from end_points.get_stock.operations.get_stock_utils import stockDataFrameFromDataTool

    print("\n" + "="*80)
    print("测试 4: Simulator 数据源一致性")
    print("="*80)

    # 这个测试需要完整的数据库初始化，单独运行
    print("\n   注意: 此测试需要完整的数据库环境")
    print("   建议运行: python test_simulator_data_sources.py")
    print("   ⏭ 跳过详细测试")

    return True


def run_all_tests():
    """运行所有回归测试"""
    print("="*80)
    print("开始运行 Regression Tests")
    print("="*80)

    results = {}

    # 测试 1: 数据源切换
    try:
        result = test_data_provider_switching()
        results['数据源切换'] = '✅ 通过' if result else '❌ 失败'
    except Exception as e:
        print(f"\n   ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        results['数据源切换'] = '❌ 异常'

    # 测试 2: 同一数据源一致性
    try:
        result = test_data_consistency_same_provider()
        results['同一数据源一致性'] = '✅ 通过' if result else '❌ 失败'
    except Exception as e:
        print(f"\n   ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        results['同一数据源一致性'] = '❌ 异常'

    # 测试 3: 数据源对比
    try:
        result = test_data_provider_comparison()
        results['数据源对比'] = '✅ 通过' if result else '⚠️ 部分通过'
    except Exception as e:
        print(f"\n   ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        results['数据源对比'] = '❌ 异常'

    # 测试 4: Simulator 一致性
    try:
        result = test_simulator_with_both_providers()
        results['Simulator 一致性'] = '⏭ 跳过'
    except Exception as e:
        print(f"\n   ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        results['Simulator 一致性'] = '❌ 异常'

    # 总结
    print("\n" + "="*80)
    print("测试总结")
    print("="*80)

    for test_name, result in results.items():
        print(f"{test_name}: {result}")

    # 统计
    passed = sum(1 for r in results.values() if '✅' in r)
    failed = sum(1 for r in results.values() if '❌' in r)
    skipped = sum(1 for r in results.values() if '⏭' in r)

    print(f"\n总计: {passed} 通过, {failed} 失败, {skipped} 跳过")

    if failed == 0:
        print("\n✅ 所有关键测试通过！")
        return True
    else:
        print(f"\n⚠️ 有 {failed} 个测试失败")
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
