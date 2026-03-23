import logging

from db.models import Rule
from end_points.common.const.consts import RuleType

logger = logging.getLogger(__name__)


def default_remote_agent_name(agent_id: str | None) -> str:
    return f"trading_agent_{agent_id}" if agent_id else "trading_agent_auto"


def default_remote_agent_description(agent_id: str | None) -> str:
    if agent_id:
        return f"Remote trading agent {agent_id}"
    return "Remote trading agent"


def build_unique_remote_agent_name(db, preferred_name: str | None, agent_id: str | None) -> str:
    candidate = (preferred_name or "").strip() or default_remote_agent_name(agent_id)
    existing = db.session.query(Rule).filter(Rule.name == candidate).first()
    if not existing:
        return candidate

    suffix = agent_id or "auto"
    candidate = f"{candidate}_{suffix}"
    existing = db.session.query(Rule).filter(Rule.name == candidate).first()
    if not existing:
        return candidate

    counter = 2
    while True:
        retry = f"{candidate}_{counter}"
        existing = db.session.query(Rule).filter(Rule.name == retry).first()
        if not existing:
            return retry
        counter += 1


def find_remote_agent_rule(db, agent_id: str | None = None, info: str | None = None):
    if agent_id:
        rule = (
            db.session.query(Rule)
            .filter(Rule.type == RuleType.remote_agent)
            .filter(Rule.agent_id == agent_id)
            .first()
        )
        if rule:
            return rule

    if info:
        rule = (
            db.session.query(Rule)
            .filter(Rule.type == RuleType.remote_agent)
            .filter(Rule.info == info)
            .first()
        )
        if rule:
            return rule

    return None


def ensure_remote_agent_rule_record(
    db,
    *,
    agent_id: str | None = None,
    info: str | None = None,
    name: str | None = None,
    description: str | None = None,
):
    normalized_agent_id = str(agent_id).strip() if agent_id is not None else None
    normalized_info = (info or "").strip()
    normalized_name = (name or "").strip() or None
    normalized_description = (description or "").strip() or default_remote_agent_description(normalized_agent_id)

    rule = find_remote_agent_rule(db, agent_id=normalized_agent_id, info=normalized_info or None)
    if rule is None:
        rule = Rule(
            name=build_unique_remote_agent_name(db, normalized_name, normalized_agent_id),
            type=RuleType.remote_agent,
            description=normalized_description[:255],
            info=normalized_info,
            agent_id=normalized_agent_id,
        )
        db.session.add(rule)
        db.session.flush()
        logger.info(
            "Ensured remote_agent rule by creating id=%s agent_id=%s info=%s",
            rule.id,
            rule.agent_id,
            rule.info,
        )
        return rule, True

    changed = False
    if normalized_agent_id and not rule.agent_id:
        rule.agent_id = normalized_agent_id
        changed = True
    if normalized_info and rule.info != normalized_info:
        rule.info = normalized_info
        changed = True
    if normalized_description and (not rule.description or rule.description == "test"):
        rule.description = normalized_description[:255]
        changed = True
    if normalized_name and rule.name != normalized_name:
        name_conflict = db.session.query(Rule).filter(Rule.name == normalized_name, Rule.id != rule.id).first()
        if not name_conflict:
            rule.name = normalized_name
            changed = True
    if changed:
        db.session.flush()
    return rule, False
