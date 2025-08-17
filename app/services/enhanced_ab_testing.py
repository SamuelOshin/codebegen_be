"""
Enhanced A/B Testing System for Phase 2: Prompt Engineering Enhancement

Provides comprehensive A/B testing framework specifically designed to measure 
the effectiveness of enhanced prompt engineering vs standard generation.

Features:
1. Enhanced vs Standard generation comparison
2. Detailed metrics collection and analysis
3. Statistical significance testing
4. Real-time performance dashboards
5. Experiment configuration management
"""

import hashlib
import json
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import statistics
import math

# Enhanced A/B Test Groups for Phase 2
ENHANCED_PROMPT_GROUPS = {
    "control_standard": 0.25,          # Standard generation (baseline)
    "enhanced_prompts": 0.25,          # Enhanced prompts only  
    "hybrid_generation": 0.25,         # Template + AI hybrid
    "full_enhancement": 0.25,          # All Phase 2 features
}

class ExperimentStatus(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    DRAFT = "draft"

class GenerationMethod(Enum):
    STANDARD = "standard"
    ENHANCED_PROMPTS = "enhanced_prompts"
    HYBRID = "hybrid"
    TEMPLATE_ONLY = "template_only"
    AI_ONLY = "ai_only"

@dataclass
class EnhancedABAssignment:
    """Enhanced A/B assignment with detailed configuration"""
    user_id: str
    group: str
    experiment_id: str
    assignment_timestamp: str
    features_enabled: Dict[str, bool]
    expected_improvement: float
    
@dataclass
class GenerationMetrics:
    """Comprehensive metrics for generation comparison"""
    generation_id: str
    user_id: str
    group: str
    method: GenerationMethod
    
    # Quality metrics
    quality_score: float
    complexity_score: float
    file_count: int
    total_lines: int
    test_coverage: float
    
    # Performance metrics
    generation_time_ms: int
    prompt_tokens: int
    response_tokens: int
    
    # User interaction metrics
    user_modifications: int
    user_satisfaction: Optional[float]
    abandoned: bool
    abandonment_stage: Optional[str]
    
    # Context metrics
    similar_projects_found: int
    user_patterns_applied: int
    template_confidence: float
    
    # Business metrics
    deployment_success: bool
    time_to_deployment: Optional[int]
    
    timestamp: str

@dataclass
class ExperimentResults:
    """Results analysis for A/B experiment"""
    experiment_id: str
    start_date: str
    end_date: str
    total_participants: int
    groups: Dict[str, int]
    
    # Statistical results
    quality_improvement: Dict[str, float]
    performance_difference: Dict[str, float]
    statistical_significance: Dict[str, float]
    confidence_intervals: Dict[str, Tuple[float, float]]
    
    # Key findings
    winner: Optional[str]
    improvement_percentage: float
    recommendation: str

class EnhancedABTestManager:
    """
    Enhanced A/B Test Manager for Phase 2 Prompt Engineering
    
    Manages experiments, assignments, and results analysis specifically
    for measuring enhanced prompt engineering effectiveness.
    """
    
    def __init__(
        self,
        groups: Optional[Dict[str, float]] = None,
        experiment_id: str = "phase2_enhanced_prompts",
        log_dir: Optional[Path] = None
    ):
        self.groups = groups or ENHANCED_PROMPT_GROUPS
        self.experiment_id = experiment_id
        self.log_dir = log_dir or Path("logs/ab_testing")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Experiment configuration
        self.experiment_config = self._load_experiment_config()
        self.status = ExperimentStatus.ACTIVE
        
        # Normalize group weights
        total = sum(self.groups.values())
        if abs(total - 1.0) > 1e-6:
            self.groups = {k: v / total for k, v in self.groups.items()}
        
        # Precompute cumulative ranges for assignment
        self._ranges = []
        cum = 0.0
        for name, weight in self.groups.items():
            start = cum
            cum += weight
            self._ranges.append((name, start, cum))
        
        # Metrics storage
        self.metrics_file = self.log_dir / f"{experiment_id}_metrics.jsonl"
        self.assignments_file = self.log_dir / f"{experiment_id}_assignments.jsonl"
        
    def _load_experiment_config(self) -> Dict[str, Any]:
        """Load experiment configuration"""
        return {
            "experiment_id": self.experiment_id,
            "description": "Phase 2: Enhanced Prompt Engineering A/B Test",
            "hypothesis": "Enhanced prompt engineering will improve generation quality by 25-35%",
            "primary_metric": "quality_score",
            "secondary_metrics": [
                "generation_time_ms",
                "user_modifications", 
                "user_satisfaction",
                "deployment_success"
            ],
            "minimum_sample_size": 100,
            "target_improvement": 0.30,  # 30% improvement target
            "significance_level": 0.05,
            "power": 0.80,
            "groups": {
                "control_standard": {
                    "description": "Standard generation (baseline)",
                    "features": {
                        "enhanced_prompts": False,
                        "context_analysis": False,
                        "user_patterns": False,
                        "hybrid_generation": False
                    }
                },
                "enhanced_prompts": {
                    "description": "Enhanced prompts with context analysis",
                    "features": {
                        "enhanced_prompts": True,
                        "context_analysis": True,
                        "user_patterns": False,
                        "hybrid_generation": False
                    }
                },
                "hybrid_generation": {
                    "description": "Template + AI hybrid approach",
                    "features": {
                        "enhanced_prompts": True,
                        "context_analysis": True,
                        "user_patterns": True,
                        "hybrid_generation": True
                    }
                },
                "full_enhancement": {
                    "description": "All Phase 2 enhanced features",
                    "features": {
                        "enhanced_prompts": True,
                        "context_analysis": True,
                        "user_patterns": True,
                        "hybrid_generation": True
                    }
                }
            }
        }
    
    def _hash01(self, user_id: str) -> float:
        """Generate deterministic hash for user assignment"""
        experiment_seed = f"{self.experiment_id}:{user_id}"
        h = hashlib.sha256(experiment_seed.encode("utf-8")).hexdigest()
        val = int(h[:8], 16)
        return (val % 10_000_000) / 10_000_000.0
    
    def assign_user(self, user_id: str) -> EnhancedABAssignment:
        """Assign user to A/B test group with enhanced configuration"""
        
        if self.status != ExperimentStatus.ACTIVE:
            # Default to control if experiment not active
            group = "control_standard"
        else:
            # Deterministic assignment based on hash
            r = self._hash01(user_id)
            group = "control_standard"  # fallback
            
            for name, start, end in self._ranges:
                if start <= r < end:
                    group = name
                    break
        
        # Get group configuration
        group_config = self.experiment_config["groups"][group]
        features_enabled = group_config["features"]
        
        # Calculate expected improvement based on features
        expected_improvement = self._calculate_expected_improvement(features_enabled)
        
        assignment = EnhancedABAssignment(
            user_id=user_id,
            group=group,
            experiment_id=self.experiment_id,
            assignment_timestamp=datetime.utcnow().isoformat() + "Z",
            features_enabled=features_enabled,
            expected_improvement=expected_improvement
        )
        
        # Log assignment
        self._log_assignment(assignment)
        
        return assignment
    
    def _calculate_expected_improvement(self, features: Dict[str, bool]) -> float:
        """Calculate expected improvement based on enabled features"""
        
        # Feature impact weights (based on Phase 2 analysis)
        feature_impacts = {
            "enhanced_prompts": 0.10,      # 10% improvement
            "context_analysis": 0.08,       # 8% improvement  
            "user_patterns": 0.12,          # 12% improvement
            "hybrid_generation": 0.15       # 15% improvement
        }
        
        total_improvement = 0.0
        for feature, enabled in features.items():
            if enabled and feature in feature_impacts:
                total_improvement += feature_impacts[feature]
        
        # Apply synergy bonus for multiple features
        enabled_count = sum(1 for f in features.values() if f)
        if enabled_count > 1:
            synergy_bonus = 0.05 * (enabled_count - 1)  # 5% per additional feature
            total_improvement += synergy_bonus
        
        return total_improvement
    
    def _log_assignment(self, assignment: EnhancedABAssignment):
        """Log user assignment to file"""
        with self.assignments_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(assignment), ensure_ascii=False) + "\n")
    
    def track_generation_metrics(self, metrics: GenerationMetrics):
        """Track comprehensive generation metrics"""
        
        # Add experiment metadata and handle enum serialization
        metrics_dict = asdict(metrics)
        metrics_dict["experiment_id"] = self.experiment_id
        
        # Convert enum to string for JSON serialization
        if "method" in metrics_dict:
            if hasattr(metrics_dict["method"], 'value'):
                metrics_dict["method"] = metrics_dict["method"].value
            else:
                metrics_dict["method"] = str(metrics_dict["method"])
        
        # Ensure file exists
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Log metrics
        with self.metrics_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(metrics_dict, ensure_ascii=False) + "\n")
    
    def get_experiment_status(self) -> Dict[str, Any]:
        """Get current experiment status and basic stats"""
        
        # Load assignments and metrics
        assignments = self._load_assignments()
        metrics = self._load_metrics()
        
        # Calculate basic stats
        group_counts = {}
        for assignment in assignments:
            group = assignment["group"]
            group_counts[group] = group_counts.get(group, 0) + 1
        
        # Calculate average metrics by group
        group_metrics = {}
        for group in self.groups.keys():
            group_data = [m for m in metrics if m["group"] == group]
            if group_data:
                group_metrics[group] = {
                    "count": len(group_data),
                    "avg_quality_score": statistics.mean(m["quality_score"] for m in group_data),
                    "avg_generation_time": statistics.mean(m["generation_time_ms"] for m in group_data),
                    "avg_user_modifications": statistics.mean(m["user_modifications"] for m in group_data),
                    "abandonment_rate": sum(1 for m in group_data if m["abandoned"]) / len(group_data)
                }
        
        return {
            "experiment_id": self.experiment_id,
            "status": self.status.value,
            "total_assignments": len(assignments),
            "total_generations": len(metrics),
            "group_assignments": group_counts,
            "group_metrics": group_metrics,
            "experiment_config": self.experiment_config
        }
    
    def _load_assignments(self) -> List[Dict[str, Any]]:
        """Load assignment data from file with error handling"""
        assignments = []
        if self.assignments_file.exists():
            with self.assignments_file.open("r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    if line.strip():
                        try:
                            assignments.append(json.loads(line))
                        except json.JSONDecodeError as e:
                            print(f"Warning: Skipping corrupted assignment on line {line_num}: {e}")
                            continue
        return assignments
    
    def _load_metrics(self) -> List[Dict[str, Any]]:
        """Load metrics data from file with error handling"""
        metrics = []
        if self.metrics_file.exists():
            with self.metrics_file.open("r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    if line.strip():
                        try:
                            metrics.append(json.loads(line))
                        except json.JSONDecodeError as e:
                            print(f"Warning: Skipping corrupted metric on line {line_num}: {e}")
                            continue
        return metrics
    
    def analyze_experiment_results(self, min_sample_size: int = 50) -> ExperimentResults:
        """Analyze experiment results with statistical significance testing"""
        
        metrics = self._load_metrics()
        
        if len(metrics) < min_sample_size:
            raise ValueError(f"Insufficient data: {len(metrics)} < {min_sample_size} minimum samples")
        
        # Group metrics by A/B group
        grouped_metrics = {}
        for metric in metrics:
            group = metric["group"]
            if group not in grouped_metrics:
                grouped_metrics[group] = []
            grouped_metrics[group].append(metric)
        
        # Calculate statistical results
        control_group = "control_standard"
        if control_group not in grouped_metrics:
            raise ValueError(f"Control group '{control_group}' not found in data")
        
        control_data = grouped_metrics[control_group]
        control_quality = [m["quality_score"] for m in control_data]
        
        results = {
            "quality_improvement": {},
            "performance_difference": {},
            "statistical_significance": {},
            "confidence_intervals": {}
        }
        
        # Analyze each treatment group vs control
        for group, data in grouped_metrics.items():
            if group == control_group:
                continue
            
            treatment_quality = [m["quality_score"] for m in data]
            treatment_time = [m["generation_time_ms"] for m in data]
            control_time = [m["generation_time_ms"] for m in control_data]
            
            # Quality improvement
            control_mean = statistics.mean(control_quality)
            treatment_mean = statistics.mean(treatment_quality)
            improvement = (treatment_mean - control_mean) / control_mean
            results["quality_improvement"][group] = improvement
            
            # Performance difference (negative is better for time)
            control_time_mean = statistics.mean(control_time)
            treatment_time_mean = statistics.mean(treatment_time)
            time_diff = (treatment_time_mean - control_time_mean) / control_time_mean
            results["performance_difference"][group] = time_diff
            
            # Statistical significance (simplified t-test)
            p_value = self._calculate_p_value(control_quality, treatment_quality)
            results["statistical_significance"][group] = p_value
            
            # Confidence interval for improvement
            ci = self._calculate_confidence_interval(control_quality, treatment_quality)
            results["confidence_intervals"][group] = ci
        
        # Determine winner
        winner = None
        best_improvement = 0
        for group, improvement in results["quality_improvement"].items():
            p_value = results["statistical_significance"][group]
            if improvement > best_improvement and p_value < 0.05:
                winner = group
                best_improvement = improvement
        
        # Generate recommendation
        if winner:
            recommendation = f"Deploy {winner} - shows {best_improvement:.1%} improvement with statistical significance"
        else:
            recommendation = "Continue experiment - no statistically significant winner yet"
        
        return ExperimentResults(
            experiment_id=self.experiment_id,
            start_date=min(m["timestamp"] for m in metrics),
            end_date=max(m["timestamp"] for m in metrics),
            total_participants=len(set(m["user_id"] for m in metrics)),
            groups={group: len(data) for group, data in grouped_metrics.items()},
            quality_improvement=results["quality_improvement"],
            performance_difference=results["performance_difference"],
            statistical_significance=results["statistical_significance"],
            confidence_intervals=results["confidence_intervals"],
            winner=winner,
            improvement_percentage=best_improvement,
            recommendation=recommendation
        )
    
    def _calculate_p_value(self, control: List[float], treatment: List[float]) -> float:
        """Simplified t-test p-value calculation"""
        if len(control) < 2 or len(treatment) < 2:
            return 1.0  # No significance with insufficient data
        
        # Welch's t-test for unequal variances
        mean1, mean2 = statistics.mean(control), statistics.mean(treatment)
        var1, var2 = statistics.variance(control), statistics.variance(treatment)
        n1, n2 = len(control), len(treatment)
        
        # Calculate t-statistic
        pooled_se = math.sqrt(var1/n1 + var2/n2)
        if pooled_se == 0:
            return 1.0
        
        t_stat = abs(mean2 - mean1) / pooled_se
        
        # Simplified p-value approximation
        # For proper implementation, use scipy.stats.ttest_ind
        if t_stat > 2.0:
            return 0.01  # Highly significant
        elif t_stat > 1.6:
            return 0.05  # Significant
        else:
            return 0.2   # Not significant
    
    def _calculate_confidence_interval(
        self, 
        control: List[float], 
        treatment: List[float],
        confidence: float = 0.95
    ) -> Tuple[float, float]:
        """Calculate confidence interval for improvement"""
        
        if len(control) < 2 or len(treatment) < 2:
            return (0.0, 0.0)
        
        mean1, mean2 = statistics.mean(control), statistics.mean(treatment)
        
        # Handle case where control mean is zero or very small
        if mean1 <= 0.001:
            return (0.0, 0.0)
        
        try:
            var1, var2 = statistics.variance(control), statistics.variance(treatment)
        except statistics.StatisticsError:
            return (0.0, 0.0)
        
        n1, n2 = len(control), len(treatment)
        
        # Standard error of difference
        se_diff = math.sqrt(var1/n1 + var2/n2)
        
        # Improvement and margin of error
        improvement = (mean2 - mean1) / mean1
        margin = 1.96 * se_diff / mean1  # 95% CI
        
        # Ensure lower bound < upper bound
        lower = improvement - margin
        upper = improvement + margin
        
        # Handle floating point precision issues
        if abs(lower - upper) < 1e-10:
            upper = lower + 1e-10
        
        return (lower, upper)
    
    def export_results_dashboard(self) -> Dict[str, Any]:
        """Export comprehensive dashboard data for visualization"""
        
        try:
            results = self.analyze_experiment_results()
            status = self.get_experiment_status()
            
            return {
                "experiment_overview": {
                    "id": self.experiment_id,
                    "status": self.status.value,
                    "description": self.experiment_config["description"],
                    "hypothesis": self.experiment_config["hypothesis"],
                    "target_improvement": self.experiment_config["target_improvement"]
                },
                "current_stats": status,
                "results_analysis": asdict(results),
                "recommendations": {
                    "winner": results.winner,
                    "confidence": "high" if results.winner else "low",
                    "action": results.recommendation,
                    "next_steps": self._generate_next_steps(results)
                },
                "visualizations": {
                    "quality_by_group": {
                        group: metrics["avg_quality_score"] 
                        for group, metrics in status["group_metrics"].items()
                    },
                    "improvements": results.quality_improvement,
                    "significance": results.statistical_significance
                }
            }
            
        except ValueError as e:
            return {
                "error": str(e),
                "current_stats": self.get_experiment_status(),
                "recommendations": {
                    "action": "Continue collecting data",
                    "next_steps": ["Reach minimum sample size", "Ensure balanced group assignment"]
                }
            }
    
    def _generate_next_steps(self, results: ExperimentResults) -> List[str]:
        """Generate actionable next steps based on results"""
        steps = []
        
        if results.winner:
            steps.append(f"Deploy {results.winner} to production")
            steps.append("Monitor production metrics for validation")
            steps.append("Plan Phase 3 enhancements")
        else:
            steps.append("Continue experiment to reach statistical significance")
            steps.append("Consider increasing sample size")
            steps.append("Review group balance and data quality")
        
        # Check for specific issues
        if any(p > 0.05 for p in results.statistical_significance.values()):
            steps.append("Increase experiment duration for statistical power")
        
        if results.improvement_percentage < 0.1:
            steps.append("Review enhancement effectiveness")
            steps.append("Consider adjusting feature combinations")
        
        return steps


# Factory function for easy initialization
def create_enhanced_ab_test_manager(
    experiment_id: str = "phase2_enhanced_prompts_v1",
    groups: Optional[Dict[str, float]] = None
) -> EnhancedABTestManager:
    """Create Enhanced A/B Test Manager for Phase 2"""
    
    return EnhancedABTestManager(
        groups=groups,
        experiment_id=experiment_id,
        log_dir=Path("logs/ab_testing/phase2")
    )


# Global instance for convenience
enhanced_ab_test_manager = create_enhanced_ab_test_manager()
