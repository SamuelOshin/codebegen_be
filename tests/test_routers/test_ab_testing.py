"""
Tests for Enhanced A/B Testing API Endpoints

Tests comprehensive A/B testing API functionality:
1. Experiment status and configuration
2. User assignment and management
3. Results analysis and reporting
4. Dashboard and export functionality
5. Health monitoring and metrics
"""

import pytest
import json
from unittest.mock import Mock, patch
from datetime import datetime
from fastapi.testclient import TestClient

from app.main import app
from app.services.enhanced_ab_testing import (
    EnhancedABTestManager,
    GenerationMetrics,
    GenerationMethod,
    ExperimentStatus,
    ExperimentResults,
    UserAssignment
)


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_ab_manager():
    """Create mock A/B testing manager"""
    manager = Mock(spec=EnhancedABTestManager)
    manager.experiment_id = "test_experiment"
    manager.status = ExperimentStatus.ACTIVE
    manager.groups = {
        "control_standard": 0.25,
        "enhanced_prompts": 0.25,
        "hybrid_generation": 0.25,
        "full_enhancement": 0.25
    }
    return manager


class TestABTestingStatusEndpoints:
    """Test A/B testing status and configuration endpoints"""
    
    @patch('app.routers.ab_testing.ab_test_manager')
    def test_get_experiment_status(self, mock_manager, client):
        """Test experiment status endpoint"""
        
        mock_manager.get_experiment_status.return_value = {
            "experiment_id": "test_experiment",
            "status": "ACTIVE",
            "total_assignments": 150,
            "total_generations": 98,
            "group_distribution": {
                "control_standard": 38,
                "enhanced_prompts": 37,
                "hybrid_generation": 39,
                "full_enhancement": 36
            },
            "group_metrics": {
                "control_standard": {
                    "avg_quality": 0.75,
                    "avg_generation_time": 3200,
                    "completion_rate": 0.68
                },
                "enhanced_prompts": {
                    "avg_quality": 0.85,
                    "avg_generation_time": 2800,
                    "completion_rate": 0.82
                }
            },
            "start_time": "2024-01-15T10:00:00Z",
            "duration_hours": 48.5
        }
        
        response = client.get("/api/v1/ab-testing/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["experiment_id"] == "test_experiment"
        assert data["status"] == "ACTIVE"
        assert data["total_assignments"] == 150
        assert "group_metrics" in data
    
    @patch('app.routers.ab_testing.ab_test_manager')
    def test_get_experiment_configuration(self, mock_manager, client):
        """Test experiment configuration endpoint"""
        
        mock_manager.experiment_id = "test_experiment"
        mock_manager.groups = {
            "control_standard": 0.25,
            "enhanced_prompts": 0.25,
            "hybrid_generation": 0.25,
            "full_enhancement": 0.25
        }
        mock_manager.status = ExperimentStatus.ACTIVE
        
        response = client.get("/api/v1/ab-testing/configuration")
        
        assert response.status_code == 200
        data = response.json()
        assert data["experiment_id"] == "test_experiment"
        assert len(data["groups"]) == 4
        assert data["groups"]["control_standard"] == 0.25


class TestABTestingAssignmentEndpoints:
    """Test user assignment endpoints"""
    
    @patch('app.routers.ab_testing.ab_test_manager')
    def test_get_user_assignment(self, mock_manager, client):
        """Test user assignment retrieval"""
        
        mock_assignment = UserAssignment(
            user_id="test_user_123",
            group="enhanced_prompts",
            experiment_id="test_experiment",
            features_enabled={
                "enhanced_prompts": True,
                "context_analysis": True,
                "user_patterns": False,
                "hybrid_generation": False
            },
            expected_improvement=0.25,
            assignment_time="2024-01-15T10:30:00Z"
        )
        
        mock_manager.assign_user.return_value = mock_assignment
        
        response = client.get("/api/v1/ab-testing/assignment/test_user_123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "test_user_123"
        assert data["group"] == "enhanced_prompts"
        assert data["features_enabled"]["enhanced_prompts"] is True
        assert data["expected_improvement"] == 0.25
    
    @patch('app.routers.ab_testing.ab_test_manager')
    def test_get_user_assignment_history(self, mock_manager, client):
        """Test user assignment history"""
        
        mock_manager._load_assignments.return_value = [
            {
                "user_id": "test_user_123",
                "group": "enhanced_prompts",
                "assignment_time": "2024-01-15T10:30:00Z",
                "experiment_id": "test_experiment"
            },
            {
                "user_id": "test_user_123",
                "group": "enhanced_prompts",
                "assignment_time": "2024-01-15T11:00:00Z",
                "experiment_id": "test_experiment"
            }
        ]
        
        response = client.get("/api/v1/ab-testing/assignment/test_user_123/history")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["assignments"]) == 2
        assert all(a["user_id"] == "test_user_123" for a in data["assignments"])
    
    @patch('app.routers.ab_testing.ab_test_manager')
    def test_batch_user_assignments(self, mock_manager, client):
        """Test batch user assignment endpoint"""
        
        def mock_assign_user(user_id):
            return UserAssignment(
                user_id=user_id,
                group="control_standard" if "control" in user_id else "enhanced_prompts",
                experiment_id="test_experiment",
                features_enabled={"enhanced_prompts": "enhanced" in user_id},
                expected_improvement=0.0 if "control" in user_id else 0.25,
                assignment_time="2024-01-15T10:30:00Z"
            )
        
        mock_manager.assign_user.side_effect = mock_assign_user
        
        request_data = {
            "user_ids": ["control_user_1", "enhanced_user_1", "control_user_2"]
        }
        
        response = client.post("/api/v1/ab-testing/assignment/batch", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["assignments"]) == 3
        assert data["assignments"][0]["user_id"] == "control_user_1"
        assert data["assignments"][0]["group"] == "control_standard"


class TestABTestingResultsEndpoints:
    """Test results analysis endpoints"""
    
    @patch('app.routers.ab_testing.ab_test_manager')
    def test_get_experiment_results(self, mock_manager, client):
        """Test experiment results endpoint"""
        
        mock_results = ExperimentResults(
            experiment_id="test_experiment",
            total_participants=200,
            quality_improvement={
                "enhanced_prompts": 0.12,
                "hybrid_generation": 0.18,
                "full_enhancement": 0.28
            },
            performance_improvement={
                "enhanced_prompts": 0.08,
                "hybrid_generation": 0.15,
                "full_enhancement": 0.25
            },
            statistical_significance={
                "enhanced_prompts": {"p_value": 0.02, "confidence_interval": [0.05, 0.19]},
                "hybrid_generation": {"p_value": 0.001, "confidence_interval": [0.11, 0.25]},
                "full_enhancement": {"p_value": 0.0001, "confidence_interval": [0.20, 0.36]}
            },
            recommendation="Deploy full_enhancement to production",
            confidence_level=0.95,
            analysis_timestamp="2024-01-17T14:30:00Z"
        )
        
        mock_manager.analyze_experiment_results.return_value = mock_results
        
        response = client.get("/api/v1/ab-testing/results")
        
        assert response.status_code == 200
        data = response.json()
        assert data["experiment_id"] == "test_experiment"
        assert data["total_participants"] == 200
        assert data["quality_improvement"]["full_enhancement"] == 0.28
        assert "statistical_significance" in data
    
    @patch('app.routers.ab_testing.ab_test_manager')
    def test_get_experiment_results_insufficient_data(self, mock_manager, client):
        """Test results endpoint with insufficient data"""
        
        mock_manager.analyze_experiment_results.side_effect = ValueError("Insufficient data for analysis")
        
        response = client.get("/api/v1/ab-testing/results")
        
        assert response.status_code == 400
        data = response.json()
        assert "Insufficient data" in data["detail"]
    
    @patch('app.routers.ab_testing.ab_test_manager')
    def test_get_results_with_filters(self, mock_manager, client):
        """Test results endpoint with time filters"""
        
        mock_results = ExperimentResults(
            experiment_id="test_experiment",
            total_participants=150,
            quality_improvement={"enhanced_prompts": 0.15},
            performance_improvement={"enhanced_prompts": 0.10},
            statistical_significance={"enhanced_prompts": {"p_value": 0.01, "confidence_interval": [0.08, 0.22]}},
            recommendation="Continue experiment",
            confidence_level=0.95,
            analysis_timestamp="2024-01-17T14:30:00Z"
        )
        
        mock_manager.analyze_experiment_results.return_value = mock_results
        
        response = client.get(
            "/api/v1/ab-testing/results",
            params={
                "start_date": "2024-01-15",
                "end_date": "2024-01-17",
                "min_sample_size": "50"
            }
        )
        
        assert response.status_code == 200
        mock_manager.analyze_experiment_results.assert_called_with(
            start_date="2024-01-15",
            end_date="2024-01-17",
            min_sample_size=50
        )


class TestABTestingDashboardEndpoints:
    """Test dashboard and visualization endpoints"""
    
    @patch('app.routers.ab_testing.ab_test_manager')
    def test_get_dashboard_data(self, mock_manager, client):
        """Test dashboard data endpoint"""
        
        mock_dashboard = {
            "experiment_overview": {
                "id": "test_experiment",
                "status": "ACTIVE",
                "duration_hours": 72.5,
                "total_participants": 250
            },
            "current_stats": {
                "quality_trends": [
                    {"group": "control_standard", "avg_quality": 0.75, "trend": "stable"},
                    {"group": "enhanced_prompts", "avg_quality": 0.85, "trend": "improving"},
                    {"group": "full_enhancement", "avg_quality": 0.92, "trend": "improving"}
                ],
                "performance_metrics": {
                    "avg_generation_time": 2650,
                    "completion_rate": 0.78,
                    "user_satisfaction": 0.82
                }
            },
            "visualizations": {
                "quality_by_group": [
                    {"group": "control_standard", "quality": 0.75, "count": 62},
                    {"group": "enhanced_prompts", "quality": 0.85, "count": 59},
                    {"group": "hybrid_generation", "quality": 0.88, "count": 65},
                    {"group": "full_enhancement", "quality": 0.92, "count": 64}
                ],
                "time_series_quality": [
                    {"hour": 0, "control_standard": 0.74, "enhanced_prompts": 0.84},
                    {"hour": 12, "control_standard": 0.75, "enhanced_prompts": 0.86},
                    {"hour": 24, "control_standard": 0.76, "enhanced_prompts": 0.87}
                ]
            },
            "recommendations": [
                "Enhanced prompts showing 13% improvement in quality",
                "Full enhancement achieving 23% improvement with statistical significance",
                "Consider deploying hybrid_generation as minimum viable improvement"
            ]
        }
        
        mock_manager.export_results_dashboard.return_value = mock_dashboard
        
        response = client.get("/api/v1/ab-testing/dashboard")
        
        assert response.status_code == 200
        data = response.json()
        assert data["experiment_overview"]["id"] == "test_experiment"
        assert len(data["current_stats"]["quality_trends"]) == 3
        assert len(data["recommendations"]) == 3
    
    @patch('app.routers.ab_testing.ab_test_manager')
    def test_export_metrics_csv(self, mock_manager, client):
        """Test metrics export in CSV format"""
        
        mock_manager._load_metrics.return_value = [
            {
                "generation_id": "gen_1",
                "user_id": "user_1",
                "group": "enhanced_prompts",
                "quality_score": 0.85,
                "generation_time_ms": 2500,
                "timestamp": "2024-01-15T10:30:00Z"
            },
            {
                "generation_id": "gen_2",
                "user_id": "user_2",
                "group": "control_standard",
                "quality_score": 0.75,
                "generation_time_ms": 3200,
                "timestamp": "2024-01-15T11:00:00Z"
            }
        ]
        
        response = client.get("/api/v1/ab-testing/metrics/export?format=csv")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        
        csv_content = response.content.decode()
        assert "generation_id,user_id,group,quality_score" in csv_content
        assert "gen_1,user_1,enhanced_prompts,0.85" in csv_content
    
    @patch('app.routers.ab_testing.ab_test_manager')
    def test_export_metrics_json(self, mock_manager, client):
        """Test metrics export in JSON format"""
        
        mock_metrics = [
            {
                "generation_id": "gen_1",
                "user_id": "user_1",
                "group": "enhanced_prompts",
                "quality_score": 0.85,
                "timestamp": "2024-01-15T10:30:00Z"
            }
        ]
        
        mock_manager._load_metrics.return_value = mock_metrics
        
        response = client.get("/api/v1/ab-testing/metrics/export?format=json")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        
        data = response.json()
        assert len(data["metrics"]) == 1
        assert data["metrics"][0]["generation_id"] == "gen_1"
    
    @patch('app.routers.ab_testing.ab_test_manager')
    def test_get_group_comparison(self, mock_manager, client):
        """Test group comparison analytics"""
        
        mock_comparison = {
            "baseline_group": "control_standard",
            "comparison_groups": ["enhanced_prompts", "hybrid_generation", "full_enhancement"],
            "metrics_comparison": {
                "quality_score": {
                    "control_standard": {"mean": 0.75, "std": 0.08, "count": 50},
                    "enhanced_prompts": {"mean": 0.85, "std": 0.06, "count": 48},
                    "hybrid_generation": {"mean": 0.88, "std": 0.05, "count": 52},
                    "full_enhancement": {"mean": 0.92, "std": 0.04, "count": 49}
                },
                "generation_time_ms": {
                    "control_standard": {"mean": 3200, "std": 400, "count": 50},
                    "enhanced_prompts": {"mean": 2800, "std": 350, "count": 48}
                }
            },
            "statistical_tests": {
                "enhanced_prompts_vs_control": {
                    "quality_score": {"p_value": 0.001, "effect_size": 0.13},
                    "generation_time_ms": {"p_value": 0.02, "effect_size": -0.12}
                }
            },
            "recommendations": [
                "Enhanced prompts show significant quality improvement (p<0.001)",
                "Full enhancement provides best overall results with 23% quality improvement"
            ]
        }
        
        mock_manager.compare_groups.return_value = mock_comparison
        
        response = client.get("/api/v1/ab-testing/comparison")
        
        assert response.status_code == 200
        data = response.json()
        assert data["baseline_group"] == "control_standard"
        assert len(data["comparison_groups"]) == 3
        assert "statistical_tests" in data


class TestABTestingFeedbackEndpoints:
    """Test user feedback and interaction tracking"""
    
    @patch('app.routers.ab_testing.ab_test_manager')
    def test_submit_user_feedback(self, mock_manager, client):
        """Test user feedback submission"""
        
        feedback_data = {
            "generation_id": "gen_123",
            "user_id": "user_123",
            "satisfaction_score": 4.2,
            "feedback_text": "The generated code was very helpful and well-structured",
            "improvement_suggestions": ["Better error handling", "More comments"],
            "would_recommend": True
        }
        
        response = client.post("/api/v1/ab-testing/user-feedback", json=feedback_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "feedback_id" in data
        
        # Verify manager was called
        mock_manager.track_user_feedback.assert_called_once()
    
    @patch('app.routers.ab_testing.ab_test_manager')
    def test_get_user_feedback_summary(self, mock_manager, client):
        """Test user feedback summary endpoint"""
        
        mock_summary = {
            "total_feedback": 125,
            "avg_satisfaction": 4.1,
            "satisfaction_by_group": {
                "control_standard": 3.7,
                "enhanced_prompts": 4.2,
                "hybrid_generation": 4.3,
                "full_enhancement": 4.5
            },
            "common_suggestions": [
                {"suggestion": "Better error handling", "count": 23},
                {"suggestion": "More comments", "count": 18},
                {"suggestion": "Improved documentation", "count": 15}
            ],
            "recommendation_rate_by_group": {
                "control_standard": 0.68,
                "enhanced_prompts": 0.78,
                "hybrid_generation": 0.82,
                "full_enhancement": 0.87
            }
        }
        
        mock_manager.get_feedback_summary.return_value = mock_summary
        
        response = client.get("/api/v1/ab-testing/user-feedback/summary")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_feedback"] == 125
        assert data["avg_satisfaction"] == 4.1
        assert len(data["common_suggestions"]) == 3


class TestABTestingHealthEndpoints:
    """Test health monitoring and system status"""
    
    @patch('app.routers.ab_testing.ab_test_manager')
    def test_health_check(self, mock_manager, client):
        """Test A/B testing system health check"""
        
        mock_health = {
            "status": "healthy",
            "experiment_active": True,
            "data_collection_rate": 0.95,
            "recent_errors": 0,
            "system_metrics": {
                "assignments_per_hour": 45,
                "generations_per_hour": 32,
                "avg_response_time_ms": 150
            },
            "alerts": [],
            "last_check": "2024-01-17T14:30:00Z"
        }
        
        mock_manager.health_check.return_value = mock_health
        
        response = client.get("/api/v1/ab-testing/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["experiment_active"] is True
        assert len(data["alerts"]) == 0
    
    @patch('app.routers.ab_testing.ab_test_manager')
    def test_health_check_with_issues(self, mock_manager, client):
        """Test health check when system has issues"""
        
        mock_health = {
            "status": "degraded",
            "experiment_active": True,
            "data_collection_rate": 0.75,
            "recent_errors": 3,
            "system_metrics": {
                "assignments_per_hour": 25,
                "generations_per_hour": 18,
                "avg_response_time_ms": 450
            },
            "alerts": [
                "Data collection rate below threshold (75% < 90%)",
                "Response time elevated (450ms > 300ms)"
            ],
            "last_check": "2024-01-17T14:30:00Z"
        }
        
        mock_manager.health_check.return_value = mock_health
        
        response = client.get("/api/v1/ab-testing/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert len(data["alerts"]) == 2


class TestABTestingErrorHandling:
    """Test error handling in A/B testing API"""
    
    @patch('app.routers.ab_testing.ab_test_manager')
    def test_user_assignment_error(self, mock_manager, client):
        """Test error handling in user assignment"""
        
        mock_manager.assign_user.side_effect = Exception("Assignment service unavailable")
        
        response = client.get("/api/v1/ab-testing/assignment/error_user")
        
        assert response.status_code == 500
        data = response.json()
        assert "Assignment service unavailable" in data["detail"]
    
    @patch('app.routers.ab_testing.ab_test_manager')
    def test_invalid_date_range(self, mock_manager, client):
        """Test error handling for invalid date ranges"""
        
        response = client.get(
            "/api/v1/ab-testing/results",
            params={
                "start_date": "invalid-date",
                "end_date": "2024-01-17"
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    @patch('app.routers.ab_testing.ab_test_manager')
    def test_export_invalid_format(self, mock_manager, client):
        """Test error handling for invalid export format"""
        
        response = client.get("/api/v1/ab-testing/metrics/export?format=xml")
        
        assert response.status_code == 400
        data = response.json()
        assert "Unsupported format" in data["detail"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
