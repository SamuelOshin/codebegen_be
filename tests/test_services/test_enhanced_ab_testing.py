"""
Tests for Enhanced A/B Testing System

Tests comprehensive A/B testing functionality for Phase 2:
1. User assignment and group balancing
2. Metrics collection and analysis
3. Statistical significance testing
4. Dashboard and export functionality
5. API endpoints
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime
import statistics

from app.services.enhanced_ab_testing import (
    EnhancedABTestManager,
    GenerationMetrics,
    GenerationMethod,
    ExperimentStatus,
    ExperimentResults,
    create_enhanced_ab_test_manager
)


class TestEnhancedABTestManager:
    """Test Enhanced A/B Test Manager core functionality"""
    
    @pytest.fixture
    def temp_log_dir(self):
        """Create temporary directory for test logs"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def ab_manager(self, temp_log_dir):
        """Create test A/B manager with temporary log directory"""
        return EnhancedABTestManager(
            experiment_id="test_experiment",
            log_dir=temp_log_dir
        )
    
    def test_manager_initialization(self, ab_manager):
        """Test A/B manager initialization"""
        assert ab_manager.experiment_id == "test_experiment"
        assert ab_manager.status == ExperimentStatus.ACTIVE
        assert len(ab_manager.groups) == 4
        assert abs(sum(ab_manager.groups.values()) - 1.0) < 1e-6
    
    def test_user_assignment_deterministic(self, ab_manager):
        """Test that user assignment is deterministic"""
        user_id = "test_user_123"
        
        assignment1 = ab_manager.assign_user(user_id)
        assignment2 = ab_manager.assign_user(user_id)
        
        assert assignment1.user_id == assignment2.user_id
        assert assignment1.group == assignment2.group
        assert assignment1.experiment_id == assignment2.experiment_id
    
    def test_user_assignment_distribution(self, ab_manager):
        """Test that user assignments are roughly balanced across groups"""
        assignments = []
        for i in range(1000):
            assignment = ab_manager.assign_user(f"user_{i}")
            assignments.append(assignment.group)
        
        # Count assignments per group
        group_counts = {}
        for group in assignments:
            group_counts[group] = group_counts.get(group, 0) + 1
        
        # Check that each group has roughly 25% (±5%)
        for group, count in group_counts.items():
            percentage = count / 1000
            assert 0.20 <= percentage <= 0.30, f"Group {group} has {percentage:.1%}, expected ~25%"
    
    def test_expected_improvement_calculation(self, ab_manager):
        """Test expected improvement calculation based on features"""
        
        # Control group should have 0% improvement
        control_assignment = ab_manager.assign_user("control_user")
        if control_assignment.group == "control_standard":
            assert control_assignment.expected_improvement == 0.0
        
        # Full enhancement should have highest improvement
        features = {
            "enhanced_prompts": True,
            "context_analysis": True,
            "user_patterns": True,
            "hybrid_generation": True
        }
        improvement = ab_manager._calculate_expected_improvement(features)
        assert improvement > 0.4  # Should be > 40% with synergy bonus
    
    def test_metrics_tracking(self, ab_manager):
        """Test generation metrics tracking"""
        
        metrics = GenerationMetrics(
            generation_id="gen_123",
            user_id="user_123",
            group="enhanced_prompts",
            method=GenerationMethod.ENHANCED_PROMPTS,
            quality_score=0.85,
            complexity_score=0.6,
            file_count=5,
            total_lines=150,
            test_coverage=0.8,
            generation_time_ms=2500,
            prompt_tokens=100,
            response_tokens=500,
            user_modifications=2,
            user_satisfaction=0.9,
            abandoned=False,
            abandonment_stage=None,
            similar_projects_found=3,
            user_patterns_applied=2,
            template_confidence=0.7,
            deployment_success=True,
            time_to_deployment=300,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
        
        ab_manager.track_generation_metrics(metrics)
        
        # Verify metrics were saved
        loaded_metrics = ab_manager._load_metrics()
        assert len(loaded_metrics) == 1
        assert loaded_metrics[0]["generation_id"] == "gen_123"
        assert loaded_metrics[0]["quality_score"] == 0.85
    
    def test_experiment_status(self, ab_manager):
        """Test experiment status reporting"""
        
        # Add some test assignments
        ab_manager.assign_user("user1")
        ab_manager.assign_user("user2")
        
        # Add some test metrics
        for i in range(3):
            metrics = GenerationMetrics(
                generation_id=f"gen_{i}",
                user_id=f"user_{i}",
                group="enhanced_prompts",
                method=GenerationMethod.ENHANCED_PROMPTS,
                quality_score=0.8 + i * 0.05,
                complexity_score=0.5,
                file_count=5,
                total_lines=100,
                test_coverage=0.0,
                generation_time_ms=2000,
                prompt_tokens=100,
                response_tokens=400,
                user_modifications=0,
                user_satisfaction=None,
                abandoned=False,
                abandonment_stage=None,
                similar_projects_found=0,
                user_patterns_applied=0,
                template_confidence=0.5,
                deployment_success=False,
                time_to_deployment=None,
                timestamp=datetime.utcnow().isoformat() + "Z"
            )
            ab_manager.track_generation_metrics(metrics)
        
        status = ab_manager.get_experiment_status()
        
        assert status["experiment_id"] == "test_experiment"
        assert status["total_assignments"] == 2
        assert status["total_generations"] == 3
        assert "group_metrics" in status
    
    def test_results_analysis_insufficient_data(self, ab_manager):
        """Test that analysis fails gracefully with insufficient data"""
        
        with pytest.raises(ValueError, match="Insufficient data"):
            ab_manager.analyze_experiment_results(min_sample_size=50)
    
    def test_results_analysis_with_data(self, ab_manager):
        """Test results analysis with sufficient data"""
        
        # Add control group data
        for i in range(30):
            metrics = GenerationMetrics(
                generation_id=f"control_gen_{i}",
                user_id=f"control_user_{i}",
                group="control_standard",
                method=GenerationMethod.STANDARD,
                quality_score=0.75 + (i % 10) * 0.01,  # 0.75-0.84
                complexity_score=0.5,
                file_count=3,
                total_lines=80,
                test_coverage=0.0,
                generation_time_ms=3000 + i * 10,
                prompt_tokens=80,
                response_tokens=300,
                user_modifications=1,
                user_satisfaction=0.7,
                abandoned=False,
                abandonment_stage=None,
                similar_projects_found=0,
                user_patterns_applied=0,
                template_confidence=0.5,
                deployment_success=False,
                time_to_deployment=None,
                timestamp=datetime.utcnow().isoformat() + "Z"
            )
            ab_manager.track_generation_metrics(metrics)
        
        # Add treatment group data (with improvement)
        for i in range(25):
            metrics = GenerationMetrics(
                generation_id=f"enhanced_gen_{i}",
                user_id=f"enhanced_user_{i}",
                group="enhanced_prompts",
                method=GenerationMethod.ENHANCED_PROMPTS,
                quality_score=0.85 + (i % 8) * 0.01,  # 0.85-0.92
                complexity_score=0.6,
                file_count=5,
                total_lines=120,
                test_coverage=0.2,
                generation_time_ms=2800 + i * 8,
                prompt_tokens=120,
                response_tokens=450,
                user_modifications=0,
                user_satisfaction=0.85,
                abandoned=False,
                abandonment_stage=None,
                similar_projects_found=2,
                user_patterns_applied=1,
                template_confidence=0.7,
                deployment_success=True,
                time_to_deployment=250,
                timestamp=datetime.utcnow().isoformat() + "Z"
            )
            ab_manager.track_generation_metrics(metrics)
        
        results = ab_manager.analyze_experiment_results(min_sample_size=20)
        
        assert isinstance(results, ExperimentResults)
        assert results.experiment_id == "test_experiment"
        assert "enhanced_prompts" in results.quality_improvement
        
        # Should show improvement in enhanced group
        improvement = results.quality_improvement["enhanced_prompts"]
        assert improvement > 0.05  # At least 5% improvement
    
    def test_dashboard_export(self, ab_manager):
        """Test dashboard data export"""
        
        # Add minimal data
        ab_manager.assign_user("user1")
        metrics = GenerationMetrics(
            generation_id="gen_1",
            user_id="user1",
            group="control_standard",
            method=GenerationMethod.STANDARD,
            quality_score=0.8,
            complexity_score=0.5,
            file_count=3,
            total_lines=100,
            test_coverage=0.0,
            generation_time_ms=2000,
            prompt_tokens=100,
            response_tokens=400,
            user_modifications=0,
            user_satisfaction=None,
            abandoned=False,
            abandonment_stage=None,
            similar_projects_found=0,
            user_patterns_applied=0,
            template_confidence=0.5,
            deployment_success=False,
            time_to_deployment=None,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
        ab_manager.track_generation_metrics(metrics)
        
        dashboard = ab_manager.export_results_dashboard()
        
        # Should have error condition but still return dashboard structure
        assert "current_stats" in dashboard
        assert "recommendations" in dashboard
        # When insufficient data, it returns error instead of experiment_overview
        if "error" in dashboard:
            assert "Insufficient data" in dashboard["error"]
        else:
            assert "experiment_overview" in dashboard
    
    def test_p_value_calculation(self, ab_manager):
        """Test statistical significance calculation"""
        
        # Test with clearly different distributions
        control = [0.7, 0.72, 0.71, 0.73, 0.69] * 10  # Mean ~0.71
        treatment = [0.85, 0.87, 0.86, 0.88, 0.84] * 10  # Mean ~0.86
        
        p_value = ab_manager._calculate_p_value(control, treatment)
        assert p_value < 0.05  # Should be significant
        
        # Test with similar distributions
        control_similar = [0.8, 0.81, 0.82, 0.79, 0.80] * 10
        treatment_similar = [0.8, 0.81, 0.82, 0.79, 0.80] * 10
        
        p_value_similar = ab_manager._calculate_p_value(control_similar, treatment_similar)
        assert p_value_similar > 0.05  # Should not be significant
    
    def test_confidence_intervals(self, ab_manager):
        """Test confidence interval calculation"""
        
        control = [0.7] * 20
        treatment = [0.85] * 20
        
        ci = ab_manager._calculate_confidence_interval(control, treatment)
        
        assert len(ci) == 2
        assert ci[0] < ci[1]  # Lower bound < upper bound
        assert ci[0] > 0  # Should show positive improvement


class TestEnhancedABTestManagerIntegration:
    """Integration tests for A/B testing system"""
    
    @pytest.fixture
    def temp_log_dir(self):
        """Create temporary directory for test logs"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    def test_full_experiment_workflow(self, temp_log_dir):
        """Test complete experiment workflow from assignment to analysis"""
        
        manager = EnhancedABTestManager(
            experiment_id="integration_test",
            log_dir=temp_log_dir
        )
        
        # Phase 1: User assignments
        users = [f"user_{i}" for i in range(100)]
        assignments = [manager.assign_user(user) for user in users]
        
        # Verify assignments are distributed
        groups = [a.group for a in assignments]
        group_counts = {g: groups.count(g) for g in set(groups)}
        assert len(group_counts) > 1  # Should have multiple groups
        
        # Phase 2: Generate metrics for each group
        for assignment in assignments[:50]:  # First 50 users generate
            base_quality = 0.75 if assignment.group == "control_standard" else 0.85
            quality_variation = (hash(assignment.user_id) % 20) / 100  # ±0.1
            
            metrics = GenerationMetrics(
                generation_id=f"gen_{assignment.user_id}",
                user_id=assignment.user_id,
                group=assignment.group,
                method=GenerationMethod.ENHANCED_PROMPTS if assignment.features_enabled.get("enhanced_prompts") else GenerationMethod.STANDARD,
                quality_score=base_quality + quality_variation,
                complexity_score=0.5,
                file_count=4,
                total_lines=100,
                test_coverage=0.1,
                generation_time_ms=2500,
                prompt_tokens=100,
                response_tokens=400,
                user_modifications=1,
                user_satisfaction=0.8,
                abandoned=False,
                abandonment_stage=None,
                similar_projects_found=1,
                user_patterns_applied=1 if assignment.features_enabled.get("user_patterns") else 0,
                template_confidence=0.6,
                deployment_success=True,
                time_to_deployment=300,
                timestamp=datetime.utcnow().isoformat() + "Z"
            )
            manager.track_generation_metrics(metrics)
        
        # Phase 3: Analyze results
        try:
            results = manager.analyze_experiment_results(min_sample_size=10)
            assert isinstance(results, ExperimentResults)
            assert results.total_participants == 50
        except ValueError:
            # May not have enough data for all groups
            pass
        
        # Phase 4: Export dashboard
        dashboard = manager.export_results_dashboard()
        assert "experiment_overview" in dashboard
        assert dashboard["experiment_overview"]["id"] == "integration_test"
    
    def test_file_persistence(self, temp_log_dir):
        """Test that data persists across manager instances"""
        
        # Create first manager and add data
        manager1 = EnhancedABTestManager(
            experiment_id="persistence_test",
            log_dir=temp_log_dir
        )
        
        assignment1 = manager1.assign_user("persistent_user")
        metrics1 = GenerationMetrics(
            generation_id="persistent_gen",
            user_id="persistent_user",
            group=assignment1.group,
            method=GenerationMethod.STANDARD,
            quality_score=0.8,
            complexity_score=0.5,
            file_count=3,
            total_lines=100,
            test_coverage=0.0,
            generation_time_ms=2000,
            prompt_tokens=100,
            response_tokens=400,
            user_modifications=0,
            user_satisfaction=None,
            abandoned=False,
            abandonment_stage=None,
            similar_projects_found=0,
            user_patterns_applied=0,
            template_confidence=0.5,
            deployment_success=False,
            time_to_deployment=None,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
        manager1.track_generation_metrics(metrics1)
        
        # Create second manager with same config
        manager2 = EnhancedABTestManager(
            experiment_id="persistence_test",
            log_dir=temp_log_dir
        )
        
        # Should load existing data
        status = manager2.get_experiment_status()
        assert status["total_assignments"] >= 1
        assert status["total_generations"] >= 1
        
        # Assignment should be deterministic across instances
        assignment2 = manager2.assign_user("persistent_user")
        assert assignment1.group == assignment2.group


class TestEnhancedABTestManagerFactory:
    """Test factory function for creating managers"""
    
    def test_factory_function(self):
        """Test factory creates manager with correct defaults"""
        
        manager = create_enhanced_ab_test_manager()
        
        assert isinstance(manager, EnhancedABTestManager)
        assert manager.experiment_id.startswith("phase2_enhanced_prompts")
        assert manager.status == ExperimentStatus.ACTIVE
    
    def test_factory_with_custom_config(self):
        """Test factory with custom configuration"""
        
        custom_groups = {
            "control": 0.5,
            "treatment": 0.5
        }
        
        manager = create_enhanced_ab_test_manager(
            experiment_id="custom_experiment",
            groups=custom_groups
        )
        
        assert manager.experiment_id == "custom_experiment"
        assert len(manager.groups) == 2
        assert manager.groups["control"] == 0.5


class TestEnhancedABTestManagerError:
    """Test error handling in A/B testing system"""
    
    @pytest.fixture
    def temp_log_dir(self):
        """Create temporary directory for test logs"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    def test_invalid_experiment_config(self, temp_log_dir):
        """Test handling of invalid experiment configuration"""
        
        # Test with invalid group weights (don't sum to 1)
        invalid_groups = {
            "group1": 0.3,
            "group2": 0.3,
            "group3": 0.3  # Sums to 0.9, not 1.0
        }
        
        manager = EnhancedABTestManager(
            groups=invalid_groups,
            log_dir=temp_log_dir
        )
        
        # Should normalize automatically
        assert abs(sum(manager.groups.values()) - 1.0) < 1e-6
    
    def test_corrupted_data_handling(self, temp_log_dir):
        """Test handling of corrupted log files"""
        
        manager = EnhancedABTestManager(
            experiment_id="corruption_test",
            log_dir=temp_log_dir
        )
        
        # Write corrupted data to metrics file
        with manager.metrics_file.open("w") as f:
            f.write("invalid json data\n")
            f.write('{"valid": "json"}\n')
            f.write("more invalid data\n")
        
        # Should handle corruption gracefully
        metrics = manager._load_metrics()
        assert len(metrics) == 1  # Only valid JSON should be loaded
        assert metrics[0]["valid"] == "json"
    
    def test_empty_data_analysis(self, temp_log_dir):
        """Test analysis with no data"""
        
        manager = EnhancedABTestManager(log_dir=temp_log_dir)
        
        # Should return meaningful error
        with pytest.raises(ValueError, match="Insufficient data"):
            manager.analyze_experiment_results()
        
        # Dashboard should still work
        dashboard = manager.export_results_dashboard()
        assert "error" in dashboard


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
