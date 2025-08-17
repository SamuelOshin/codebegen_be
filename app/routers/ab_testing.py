"""
A/B Testing Management API Endpoints

Provides API endpoints for managing and viewing A/B testing experiments,
specifically for Phase 2 Enhanced Prompt Engineering validation.

Features:
1. Experiment status and configuration
2. Real-time results dashboard
3. Statistical analysis and recommendations  
4. User assignment management
5. Metrics export and visualization
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, Optional, List
import json
from datetime import datetime

from app.auth.dependencies import get_current_user
from app.schemas.user import UserResponse as User
from app.services.enhanced_ab_testing import (
    enhanced_ab_test_manager,
    ExperimentResults,
    GenerationMetrics,
    EnhancedABAssignment
)

router = APIRouter(prefix="/ab-testing", tags=["A/B Testing"])

@router.get("/status")
async def get_experiment_status(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get current A/B testing experiment status and basic statistics"""
    
    try:
        status = enhanced_ab_test_manager.get_experiment_status()
        return {
            "success": True,
            "data": status,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get experiment status: {str(e)}")

@router.get("/assignment/{user_id}")
async def get_user_assignment(
    user_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get A/B testing assignment for a specific user"""
    
    try:
        assignment = enhanced_ab_test_manager.assign_user(user_id)
        return {
            "success": True,
            "data": {
                "user_id": assignment.user_id,
                "group": assignment.group,
                "experiment_id": assignment.experiment_id,
                "features_enabled": assignment.features_enabled,
                "expected_improvement": assignment.expected_improvement,
                "assignment_timestamp": assignment.assignment_timestamp
            },
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user assignment: {str(e)}")

@router.get("/results")
async def get_experiment_results(
    min_sample_size: int = Query(default=50, description="Minimum sample size for analysis"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get comprehensive A/B testing experiment results with statistical analysis"""
    
    try:
        results = enhanced_ab_test_manager.analyze_experiment_results(min_sample_size)
        
        return {
            "success": True,
            "data": {
                "experiment_id": results.experiment_id,
                "experiment_period": {
                    "start_date": results.start_date,
                    "end_date": results.end_date
                },
                "participants": {
                    "total": results.total_participants,
                    "by_group": results.groups
                },
                "quality_improvements": results.quality_improvement,
                "performance_differences": results.performance_difference,
                "statistical_significance": results.statistical_significance,
                "confidence_intervals": results.confidence_intervals,
                "recommendation": {
                    "winner": results.winner,
                    "improvement_percentage": results.improvement_percentage,
                    "action": results.recommendation
                }
            },
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except ValueError as ve:
        return {
            "success": False,
            "error": str(ve),
            "message": "Insufficient data for statistical analysis",
            "current_sample_size": enhanced_ab_test_manager.get_experiment_status()["total_generations"],
            "required_sample_size": min_sample_size,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze results: {str(e)}")

@router.get("/dashboard")
async def get_experiment_dashboard(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get comprehensive dashboard data for A/B testing visualization"""
    
    try:
        dashboard_data = enhanced_ab_test_manager.export_results_dashboard()
        return {
            "success": True,
            "data": dashboard_data,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        # Return partial data even if analysis fails
        status = enhanced_ab_test_manager.get_experiment_status()
        return {
            "success": False,
            "error": str(e),
            "partial_data": status,
            "message": "Dashboard generated with limited data due to analysis error",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

@router.get("/metrics/export")
async def export_metrics(
    format: str = Query(default="json", description="Export format: json, csv"),
    group_filter: Optional[str] = Query(default=None, description="Filter by A/B group"),
    start_date: Optional[str] = Query(default=None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(default=None, description="End date (ISO format)"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Export A/B testing metrics data for external analysis"""
    
    try:
        # Load raw metrics data
        metrics = enhanced_ab_test_manager._load_metrics()
        assignments = enhanced_ab_test_manager._load_assignments()
        
        # Apply filters
        filtered_metrics = metrics
        
        if group_filter:
            filtered_metrics = [m for m in filtered_metrics if m["group"] == group_filter]
        
        if start_date:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            filtered_metrics = [m for m in filtered_metrics 
                              if datetime.fromisoformat(m["timestamp"].replace('Z', '+00:00')) >= start_dt]
        
        if end_date:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            filtered_metrics = [m for m in filtered_metrics 
                              if datetime.fromisoformat(m["timestamp"].replace('Z', '+00:00')) <= end_dt]
        
        if format.lower() == "csv":
            # Convert to CSV-like structure
            csv_data = []
            for metric in filtered_metrics:
                csv_data.append({
                    "generation_id": metric["generation_id"],
                    "user_id": metric["user_id"],
                    "group": metric["group"],
                    "method": metric["method"],
                    "quality_score": metric["quality_score"],
                    "generation_time_ms": metric["generation_time_ms"],
                    "file_count": metric["file_count"],
                    "total_lines": metric["total_lines"],
                    "abandoned": metric["abandoned"],
                    "timestamp": metric["timestamp"]
                })
            
            return {
                "success": True,
                "format": "csv",
                "data": csv_data,
                "count": len(csv_data),
                "filters_applied": {
                    "group": group_filter,
                    "start_date": start_date,
                    "end_date": end_date
                },
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        
        else:  # JSON format
            return {
                "success": True,
                "format": "json",
                "data": {
                    "metrics": filtered_metrics,
                    "assignments": assignments
                },
                "count": len(filtered_metrics),
                "filters_applied": {
                    "group": group_filter,
                    "start_date": start_date,
                    "end_date": end_date
                },
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export metrics: {str(e)}")

@router.get("/groups")
async def get_experiment_groups(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get A/B testing group configuration and details"""
    
    try:
        config = enhanced_ab_test_manager.experiment_config
        status = enhanced_ab_test_manager.get_experiment_status()
        
        groups_info = []
        for group_name, group_config in config["groups"].items():
            group_stats = status["group_metrics"].get(group_name, {})
            
            groups_info.append({
                "name": group_name,
                "description": group_config["description"],
                "features": group_config["features"],
                "weight": enhanced_ab_test_manager.groups.get(group_name, 0),
                "assignment_count": status["group_assignments"].get(group_name, 0),
                "generation_count": group_stats.get("count", 0),
                "avg_quality_score": group_stats.get("avg_quality_score", 0),
                "avg_generation_time": group_stats.get("avg_generation_time", 0),
                "abandonment_rate": group_stats.get("abandonment_rate", 0)
            })
        
        return {
            "success": True,
            "data": {
                "experiment_id": config["experiment_id"],
                "description": config["description"],
                "hypothesis": config["hypothesis"],
                "target_improvement": config["target_improvement"],
                "groups": groups_info,
                "total_groups": len(groups_info)
            },
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get group information: {str(e)}")

@router.post("/user-feedback")
async def track_user_feedback(
    generation_id: str,
    satisfaction_score: float = Query(description="User satisfaction (0.0-1.0)"),
    modifications_count: int = Query(description="Number of user modifications"),
    deployed: bool = Query(default=False, description="Whether project was deployed"),
    feedback_notes: Optional[str] = Query(default=None, description="Additional feedback"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Track user feedback and interaction metrics for A/B testing"""
    
    try:
        # Load existing metrics to find the generation
        metrics = enhanced_ab_test_manager._load_metrics()
        
        # Find the specific generation
        target_metric = None
        for metric in metrics:
            if metric["generation_id"] == generation_id:
                target_metric = metric
                break
        
        if not target_metric:
            raise HTTPException(status_code=404, detail="Generation not found")
        
        # Update the metric with user feedback
        updated_metric = GenerationMetrics(
            generation_id=target_metric["generation_id"],
            user_id=target_metric["user_id"],
            group=target_metric["group"],
            method=target_metric["method"],
            quality_score=target_metric["quality_score"],
            complexity_score=target_metric["complexity_score"],
            file_count=target_metric["file_count"],
            total_lines=target_metric["total_lines"],
            test_coverage=target_metric["test_coverage"],
            generation_time_ms=target_metric["generation_time_ms"],
            prompt_tokens=target_metric["prompt_tokens"],
            response_tokens=target_metric["response_tokens"],
            user_modifications=modifications_count,
            user_satisfaction=satisfaction_score,
            abandoned=target_metric["abandoned"],
            abandonment_stage=target_metric["abandonment_stage"],
            similar_projects_found=target_metric["similar_projects_found"],
            user_patterns_applied=target_metric["user_patterns_applied"],
            template_confidence=target_metric["template_confidence"],
            deployment_success=deployed,
            time_to_deployment=None,  # Could be calculated from timestamp
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
        
        # Re-track the updated metric
        enhanced_ab_test_manager.track_generation_metrics(updated_metric)
        
        return {
            "success": True,
            "message": "User feedback tracked successfully",
            "data": {
                "generation_id": generation_id,
                "satisfaction_score": satisfaction_score,
                "modifications_count": modifications_count,
                "deployed": deployed,
                "feedback_notes": feedback_notes
            },
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to track user feedback: {str(e)}")

@router.get("/comparison")
async def get_group_comparison(
    metric: str = Query(default="quality_score", description="Metric to compare"),
    baseline_group: str = Query(default="control_standard", description="Baseline group for comparison"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get detailed comparison between A/B testing groups for a specific metric"""
    
    try:
        metrics = enhanced_ab_test_manager._load_metrics()
        
        # Group metrics by A/B group
        grouped_data = {}
        for m in metrics:
            group = m["group"]
            if group not in grouped_data:
                grouped_data[group] = []
            
            if metric in m:
                grouped_data[group].append(m[metric])
        
        # Calculate comparison statistics
        comparison_results = {}
        baseline_values = grouped_data.get(baseline_group, [])
        
        if not baseline_values:
            raise HTTPException(status_code=404, detail=f"Baseline group '{baseline_group}' not found or has no data")
        
        baseline_mean = sum(baseline_values) / len(baseline_values)
        
        for group, values in grouped_data.items():
            if not values or group == baseline_group:
                continue
            
            group_mean = sum(values) / len(values)
            improvement = (group_mean - baseline_mean) / baseline_mean if baseline_mean != 0 else 0
            
            comparison_results[group] = {
                "sample_size": len(values),
                "mean": group_mean,
                "baseline_mean": baseline_mean,
                "improvement": improvement,
                "improvement_percentage": improvement * 100,
                "min": min(values),
                "max": max(values)
            }
        
        return {
            "success": True,
            "data": {
                "metric": metric,
                "baseline_group": baseline_group,
                "baseline_sample_size": len(baseline_values),
                "baseline_mean": baseline_mean,
                "comparisons": comparison_results
            },
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate comparison: {str(e)}")

@router.get("/health")
async def get_ab_testing_health() -> Dict[str, Any]:
    """Get A/B testing system health and configuration status"""
    
    try:
        status = enhanced_ab_test_manager.get_experiment_status()
        
        # Calculate health metrics
        total_assignments = status["total_assignments"]
        total_generations = status["total_generations"]
        group_balance = status["group_assignments"]
        
        # Check group balance (should be roughly equal)
        expected_per_group = total_assignments / len(enhanced_ab_test_manager.groups) if total_assignments > 0 else 0
        balance_issues = []
        
        for group, count in group_balance.items():
            if expected_per_group > 0:
                deviation = abs(count - expected_per_group) / expected_per_group
                if deviation > 0.2:  # More than 20% deviation
                    balance_issues.append(f"Group {group} has {deviation:.1%} deviation from expected")
        
        # Check data collection rate
        conversion_rate = total_generations / total_assignments if total_assignments > 0 else 0
        
        health_status = "healthy"
        if balance_issues or conversion_rate < 0.8:
            health_status = "warning"
        if total_assignments < 10 or conversion_rate < 0.5:
            health_status = "unhealthy"
        
        return {
            "success": True,
            "health_status": health_status,
            "data": {
                "experiment_id": enhanced_ab_test_manager.experiment_id,
                "experiment_status": enhanced_ab_test_manager.status.value,
                "total_assignments": total_assignments,
                "total_generations": total_generations,
                "conversion_rate": conversion_rate,
                "group_balance": group_balance,
                "balance_issues": balance_issues,
                "data_quality": {
                    "sufficient_sample_size": total_generations >= 50,
                    "balanced_groups": len(balance_issues) == 0,
                    "good_conversion": conversion_rate >= 0.8
                }
            },
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        return {
            "success": False,
            "health_status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
