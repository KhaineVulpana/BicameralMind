"""Quality Analyzer - Identifies low-quality bullets for pruning"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from .bullet import Bullet, BulletStatus

logger = logging.getLogger(__name__)


class PrunePolicy(Enum):
    """Pruning policy levels"""
    AGGRESSIVE = "aggressive"
    BALANCED = "balanced"
    CONSERVATIVE = "conservative"


class PruneReason(Enum):
    """Reasons for pruning a bullet"""
    HARMFUL_RATIO = "harmful_ratio"  # Too many harmful vs helpful
    NEVER_USED_OLD = "never_used_old"  # Never used and old
    QUARANTINE_EXPIRED = "quarantine_expired"  # Stuck in quarantine too long
    LOW_CONFIDENCE = "low_confidence"  # Very low confidence
    SUPERSEDED = "superseded"  # Replaced by better bullet


@dataclass
class QualityMetrics:
    """Quality metrics for a bullet"""
    bullet_id: str
    quality_score: float
    helpful_ratio: float
    age_days: int
    usage_count: int
    days_since_last_use: Optional[int]
    is_low_quality: bool
    prune_reasons: List[PruneReason]


class QualityAnalyzer:
    """
    Quality Analyzer System

    Analyzes bullet quality based on:
    - helpful/harmful ratio
    - Usage frequency
    - Age and recency
    - Confidence scores
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize quality analyzer

        Args:
            config: Configuration dict
        """
        self.config = config or {}

        # Policy settings (can be overridden per-run)
        self.default_policy = PrunePolicy(
            self.config.get("prune_policy", "balanced")
        )

        # Thresholds for balanced policy (default)
        self.min_age_days = self.config.get("prune_min_age_days", 14)
        self.harmful_ratio = self.config.get("prune_harmful_ratio", 1.5)
        self.quarantine_age_days = self.config.get("prune_quarantine_age_days", 30)
        self.low_confidence_threshold = self.config.get("low_confidence_threshold", 0.2)

        # Statistics
        self.stats = {
            "total_analyses": 0,
            "low_quality_found": 0,
        }

        logger.info(f"QualityAnalyzer initialized (policy={self.default_policy.value})")

    def analyze_bullet(
        self,
        bullet: Bullet,
        policy: Optional[PrunePolicy] = None
    ) -> QualityMetrics:
        """
        Analyze a single bullet's quality

        Args:
            bullet: Bullet to analyze
            policy: Pruning policy to use

        Returns:
            QualityMetrics
        """
        policy = policy or self.default_policy

        # Calculate metrics
        age_days = self._calculate_age_days(bullet)
        usage_count = bullet.helpful_count + bullet.harmful_count

        if usage_count > 0:
            helpful_ratio = bullet.helpful_count / usage_count
        else:
            helpful_ratio = 0.0

        days_since_last_use = None
        if bullet.last_used_at:
            days_since_last_use = (datetime.now() - bullet.last_used_at).days

        # Calculate quality score
        quality_score = self._calculate_quality_score(bullet)

        # Determine if low quality and reasons
        is_low_quality, reasons = self._is_low_quality(bullet, policy, age_days)

        return QualityMetrics(
            bullet_id=bullet.id,
            quality_score=quality_score,
            helpful_ratio=helpful_ratio,
            age_days=age_days,
            usage_count=usage_count,
            days_since_last_use=days_since_last_use,
            is_low_quality=is_low_quality,
            prune_reasons=reasons
        )

    def find_low_quality(
        self,
        bullets: List[Bullet],
        policy: Optional[PrunePolicy] = None
    ) -> List[Tuple[Bullet, QualityMetrics]]:
        """
        Find low-quality bullets from a list

        Args:
            bullets: List of bullets to analyze
            policy: Pruning policy to use

        Returns:
            List of (Bullet, QualityMetrics) tuples for low-quality bullets
        """
        policy = policy or self.default_policy

        logger.info(f"Analyzing {len(bullets)} bullets (policy={policy.value})")

        low_quality = []

        for bullet in bullets:
            metrics = self.analyze_bullet(bullet, policy)

            if metrics.is_low_quality:
                low_quality.append((bullet, metrics))

        logger.info(f"Found {len(low_quality)} low-quality bullets")

        self.stats["total_analyses"] += len(bullets)
        self.stats["low_quality_found"] += len(low_quality)

        return low_quality

    def _calculate_age_days(self, bullet: Bullet) -> int:
        """Calculate bullet age in days"""
        # Handle both timezone-aware and naive datetimes
        now = datetime.now()
        if bullet.created_at.tzinfo is not None:
            # created_at is timezone-aware, make now aware too
            from datetime import timezone
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            created_at = bullet.created_at.replace(tzinfo=None)
        else:
            created_at = bullet.created_at
        return (now - created_at).days

    def _calculate_quality_score(self, bullet: Bullet) -> float:
        """
        Calculate overall quality score (0.0-1.0)

        Higher is better
        """
        total_uses = bullet.helpful_count + bullet.harmful_count

        if total_uses == 0:
            # No usage data, base on confidence only
            return bullet.confidence * 0.5  # Penalize unused

        # Helpful ratio
        helpful_ratio = bullet.helpful_count / total_uses

        # Usage weight (log scale)
        import numpy as np
        usage_weight = np.log1p(total_uses) / 10.0  # Normalize

        # Confidence weight
        confidence_weight = bullet.confidence

        # Combined score
        score = (
            helpful_ratio * 0.5 +
            min(usage_weight, 1.0) * 0.3 +
            confidence_weight * 0.2
        )

        return min(max(score, 0.0), 1.0)

    def _is_low_quality(
        self,
        bullet: Bullet,
        policy: PrunePolicy,
        age_days: int
    ) -> Tuple[bool, List[PruneReason]]:
        """
        Determine if bullet is low quality

        Args:
            bullet: Bullet to check
            policy: Pruning policy
            age_days: Bullet age in days

        Returns:
            (is_low_quality, list of reasons)
        """
        reasons = []

        # Get thresholds based on policy
        thresholds = self._get_policy_thresholds(policy)

        total_uses = bullet.helpful_count + bullet.harmful_count

        # Check harmful ratio
        if total_uses > 0:
            if bullet.harmful_count > bullet.helpful_count * thresholds["harmful_ratio"]:
                reasons.append(PruneReason.HARMFUL_RATIO)

        # Check never used but old
        if total_uses == 0 and age_days > thresholds["never_used_age"]:
            reasons.append(PruneReason.NEVER_USED_OLD)

        # Check quarantined too long
        if (bullet.status == BulletStatus.QUARANTINED and
            age_days > thresholds["quarantine_age"]):
            reasons.append(PruneReason.QUARANTINE_EXPIRED)

        # Check low confidence
        if (bullet.confidence < self.low_confidence_threshold and
            total_uses == 0 and
            age_days > thresholds["low_confidence_age"]):
            reasons.append(PruneReason.LOW_CONFIDENCE)

        return (len(reasons) > 0, reasons)

    def _get_policy_thresholds(self, policy: PrunePolicy) -> Dict[str, Any]:
        """Get thresholds for a given policy"""
        if policy == PrunePolicy.AGGRESSIVE:
            return {
                "harmful_ratio": 1.0,  # Equal or more harmful than helpful
                "never_used_age": 7,  # 1 week
                "quarantine_age": 14,  # 2 weeks
                "low_confidence_age": 7,
            }

        elif policy == PrunePolicy.CONSERVATIVE:
            return {
                "harmful_ratio": 2.0,  # Twice as harmful
                "never_used_age": 30,  # 1 month
                "quarantine_age": 60,  # 2 months
                "low_confidence_age": 30,
            }

        else:  # BALANCED
            return {
                "harmful_ratio": self.harmful_ratio,
                "never_used_age": self.min_age_days,
                "quarantine_age": self.quarantine_age_days,
                "low_confidence_age": self.min_age_days,
            }

    def get_quality_distribution(
        self,
        bullets: List[Bullet]
    ) -> Dict[str, int]:
        """Get distribution of bullet quality"""
        distribution = {
            "excellent": 0,  # quality > 0.8
            "good": 0,  # 0.6 - 0.8
            "fair": 0,  # 0.4 - 0.6
            "poor": 0,  # 0.2 - 0.4
            "very_poor": 0,  # < 0.2
        }

        for bullet in bullets:
            metrics = self.analyze_bullet(bullet)
            score = metrics.quality_score

            if score > 0.8:
                distribution["excellent"] += 1
            elif score > 0.6:
                distribution["good"] += 1
            elif score > 0.4:
                distribution["fair"] += 1
            elif score > 0.2:
                distribution["poor"] += 1
            else:
                distribution["very_poor"] += 1

        return distribution

    def get_stats(self) -> Dict[str, Any]:
        """Get analyzer statistics"""
        return {
            **self.stats,
            "policy": self.default_policy.value,
            "thresholds": self._get_policy_thresholds(self.default_policy),
        }
