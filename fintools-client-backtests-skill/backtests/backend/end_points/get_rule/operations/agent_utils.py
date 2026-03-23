from datetime import datetime
import asyncio
import pandas as pd
import logging
import sys
from pathlib import Path

from db.models import Simulator, AgentTrading, Rule, RulePool, PoolStock
from end_points.common.const.consts import Trade
from end_points.common.utils.trading_agent_sync import sync_trading_agent_into_backtests
from end_points.get_simulator.operations.get_simulator_utils import update_sim_model
from end_points.get_rule.operations.skill_agent_adapter import (
    execute_trading_agent_via_skill,
    extract_trading_action,
)

REPO_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.trading_run_store import record_trading_agent_run

logger = logging.getLogger(__name__)


def get_remote_rule_record(db, rule_id):
    rule_record = db.session.query(Rule).filter(Rule.id == rule_id).first()
    if not rule_record:
        return {
            'success': False,
            'message': f'Rule {rule_id} not found',
        }
    if rule_record.type != 'remote_agent':
        return {
            'success': False,
            'message': f'Unsupported rule type for backtests: {rule_record.type}',
        }
    base_url = rule_record.info
    if not base_url:
        return {
            'success': False,
            'message': 'Remote agent must have a base_url in info field',
        }
    return {
        'success': True,
        'rule': rule_record,
        'base_url': base_url,
    }


def get_agent_buying_stocks(db, rule_id):
    """
    Get all stocks from pools that belong to this rule.

    Args:
        db: Database session
        rule_id: Rule ID

    Returns:
        List of stock codes (strings) without exchange suffix
    """
    # Get distinct pool_ids for this rule_id
    pool_ids = db.session.query(RulePool.pool_id)\
        .filter(RulePool.rule_id == rule_id)\
        .distinct()\
        .all()

    pool_ids = [p[0] for p in pool_ids if p[0]]

    if not pool_ids:
        return []

    # Get all stock codes for these pool_ids
    stocks = db.session.query(PoolStock.stock_code)\
        .filter(PoolStock.pool_id.in_(pool_ids))\
        .distinct()\
        .all()

    # Strip exchange suffix (e.g., '000001.SZ' -> '000001')
    stock_list = [s.split('.')[0] if '.' in s else s for (s,) in stocks]
    return stock_list


def get_rule_execution_plan(db, rule_id):
    rule_info = get_remote_rule_record(db, rule_id)
    if not rule_info.get('success'):
        return {
            'success': False,
            'needs_pool': False,
            'message': rule_info['message'],
            'stock_count': 0,
            'executed_count': 0,
            'failed_count': 0,
        }

    pool_count = db.session.query(RulePool).filter(RulePool.rule_id == rule_id).count()
    stock_list = get_agent_buying_stocks(db, rule_id)
    if not stock_list:
        message = 'Rule has no assigned pool. Assign a pool before running this agent.'
        if pool_count > 0:
            message = 'Rule pools do not contain any stocks. Add stocks before running this agent.'
        return {
            'success': False,
            'needs_pool': True,
            'message': message,
            'rule': rule_info['rule'],
            'base_url': rule_info['base_url'],
            'pool_count': pool_count,
            'stock_count': 0,
            'executed_count': 0,
            'failed_count': 0,
            'stock_list': [],
        }

    return {
        'success': True,
        'needs_pool': False,
        'message': 'Execution plan ready',
        'rule': rule_info['rule'],
        'base_url': rule_info['base_url'],
        'pool_count': pool_count,
        'stock_count': len(stock_list),
        'stock_list': stock_list,
    }

def persist_trading_result_and_sync(db, rule_record, stock_code, action, result, mode="streaming", trade_date=None):
    trade_date = trade_date or datetime.now()
    persisted_run = record_trading_agent_run(
        stock_code=stock_code,
        mode=mode,
        result=result,
        action=action,
        agent_id=rule_record.agent_id,
        agent_name=rule_record.name,
        created_at=trade_date if isinstance(trade_date, datetime) else datetime.combine(trade_date, datetime.min.time()),
        updated_at=trade_date if isinstance(trade_date, datetime) else datetime.combine(trade_date, datetime.min.time()),
    )
    sync_trading_agent_into_backtests(db)
    return persisted_run

def run_sim_agent(db, agent_sim_id):
    agent_rule_id = db.session.query(Simulator.rule_id).filter(Simulator.id == agent_sim_id).scalar()
    record = db.session.query(AgentTrading).filter(AgentTrading.rule_id == agent_rule_id).all()
    indicating_items = []
    for each_item in record:
        stock_code = each_item.stock
        indicating_date = pd.Timestamp(each_item.trading_date)
        indi_item = {
            'stock_code': stock_code,
            'indicating_date': indicating_date,
        }
        indicating_items.append(indi_item)

    indicating_date = update_sim_model(db, agent_sim_id, indicating_items)
    return indicating_date


def run_async(coro):
    """Run async code in a separate thread to avoid event-loop conflicts."""
    import concurrent.futures

    def run_in_thread():
        return asyncio.run(coro)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(run_in_thread)
        return future.result()


def run_agent_for_stock(db, rule_id, stock_code):
    """
    Run a remote agent rule for a single stock.

    Args:
        db: Database session
        rule_id: Remote agent rule ID
        stock_code: Stock code to analyze

    Returns:
        dict: {
            'success': bool,
            'stock_code': str,
            'indicating': str,
            'result': bool,
            'error': str (if failed)
        }
    """
    indicating_date = datetime.now().date()
    print(f'Start running agent {rule_id} for {stock_code}...')

    rule_info = get_remote_rule_record(db, rule_id)
    if not rule_info.get('success'):
        return {
            'success': False,
            'stock_code': stock_code,
            'error': rule_info['message']
        }
    rule_record = rule_info['rule']
    base_url = rule_info['base_url']

    try:
        clean_stock_code = stock_code.split('.')[0] if '.' in stock_code else stock_code
        result = run_async(
            execute_agent_with_skill_adapter(clean_stock_code, base_url)
        )
        action = extract_trading_action(result)
        is_indicating = action == Trade.buy
        indicating = Trade.indicating if is_indicating else Trade.not_indicating
        persist_trading_result_and_sync(
            db,
            rule_record,
            stock_code,
            action,
            result,
            mode="streaming",
            trade_date=datetime.combine(indicating_date, datetime.min.time()),
        )
        print(f'Result from Remote Agent {rule_id}: {stock_code} is {indicating}!')

        rule_record.updated_at = datetime.now()
        db.session.commit()

        return {
            'success': True,
            'stock_code': stock_code,
            'indicating': indicating,
            'result': is_indicating,
            'action': action,
        }

    except Exception as e:
        print(f'Error running remote agent {rule_id} for stock {stock_code}: {e}')
        import traceback
        traceback.print_exc()
        db.session.commit()

        return {
            'success': False,
            'stock_code': stock_code,
            'error': str(e)
        }


def run_agent(db, rule_id):
    """
    Run an agent-type rule for all stocks in its pools.

    Args:
        db: Database session
        rule_id: Agent rule ID
    """
    execution_plan = get_rule_execution_plan(db, rule_id)
    if not execution_plan.get('success'):
        return execution_plan

    buying_stocks_list = execution_plan['stock_list']
    print(f'Buying stocks for today are: {buying_stocks_list}')

    executed_count = 0
    failed_count = 0
    errors = []
    for stock_code in buying_stocks_list:
        result = run_agent_for_stock(db, rule_id, stock_code)
        if result.get('success'):
            executed_count += 1
        else:
            failed_count += 1
            errors.append({
                'stock_code': stock_code,
                'error': result.get('error', 'unknown error'),
            })

    return {
        'success': failed_count == 0,
        'stock_count': len(buying_stocks_list),
        'executed_count': executed_count,
        'failed_count': failed_count,
        'errors': errors,
        'message': 'Agent execution completed' if failed_count == 0 else 'Agent execution completed with failures',
    }


async def execute_agent_with_skill_adapter(stock_code, base_url):
    return await execute_trading_agent_via_skill(stock_code, base_url)
