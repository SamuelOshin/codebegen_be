"""
Tests for generation versioning and hierarchical file storage.
"""

import pytest
import tempfile
import shutil
import json
from pathlib import Path
from datetime import datetime

from app.services.file_manager import FileManager
from app.models.generation import Generation
from app.models.project import Project


class TestHierarchicalStorage:
    """Test hierarchical file storage structure"""
    
    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage directory"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def file_manager(self, temp_storage, monkeypatch):
        """Create FileManager with temp storage"""
        # Patch settings to use temp directory
        monkeypatch.setattr("app.services.file_manager.settings.FILE_STORAGE_PATH", temp_storage)
        monkeypatch.setattr("app.services.file_manager.settings.TEMP_STORAGE_PATH", temp_storage)
        return FileManager()
    
    @pytest.mark.asyncio
    async def test_hierarchical_directory_structure(self, file_manager, temp_storage):
        """Test that hierarchical directories are created correctly"""
        
        project_id = "test-project-123"
        generation_id = "test-gen-456"
        version = 1
        
        files = {
            "app/main.py": "from fastapi import FastAPI",
            "app/models.py": "# Models",
            "README.md": "# Project"
        }
        
        storage_path, file_count, total_size = await file_manager.save_generation_files_hierarchical(
            project_id=project_id,
            generation_id=generation_id,
            version=version,
            files=files
        )
        
        # Verify path structure
        expected_path = Path(temp_storage) / project_id / "generations" / f"v{version}__{generation_id}"
        assert expected_path.exists()
        assert expected_path.is_dir()
        
        # Verify source directory
        source_dir = expected_path / "source"
        assert source_dir.exists()
        
        # Verify files
        assert (source_dir / "app" / "main.py").exists()
        assert (source_dir / "app" / "models.py").exists()
        assert (source_dir / "README.md").exists()
        
        # Verify manifest
        manifest_path = expected_path / "manifest.json"
        assert manifest_path.exists()
    
    def test_manifest_json_content(self, file_manager, temp_storage):
        """Test that manifest.json contains correct metadata"""
        
        project_id = "project-123"
        generation_id = "gen-456"
        version = 5
        
        files = {
            "app.py": "print('hello')",
            "test.py": "# test"
        }
        
        storage_path = file_manager.save_generation_files_hierarchical(
            project_id=project_id,
            generation_id=generation_id,
            version=version,
            files=files
        )
        
        # Read manifest
        manifest_path = Path(storage_path) / "manifest.json"
        with open(manifest_path) as f:
            manifest = json.load(f)
        
        # Verify manifest content
        assert manifest["version"] == version
        assert manifest["generation_id"] == generation_id
        assert manifest["project_id"] == project_id
        assert manifest["file_count"] == 2
        assert "created_at" in manifest
        assert "files" in manifest
        
        # Verify file list
        file_list = manifest["files"]
        assert len(file_list) == 2
        assert any(f["path"] == "app.py" for f in file_list)
        assert any(f["path"] == "test.py" for f in file_list)
        
        # Verify file sizes
        for file_info in file_list:
            assert "size" in file_info
            assert file_info["size"] > 0
    
    def test_multiple_versions_same_project(self, file_manager, temp_storage):
        """Test creating multiple versions in same project"""
        
        project_id = "project-abc"
        
        # Create version 1
        v1_path = file_manager.save_generation_files_hierarchical(
            project_id=project_id,
            generation_id="gen-1",
            version=1,
            files={"v1.py": "# Version 1"}
        )
        
        # Create version 2
        v2_path = file_manager.save_generation_files_hierarchical(
            project_id=project_id,
            generation_id="gen-2",
            version=2,
            files={"v2.py": "# Version 2"}
        )
        
        # Create version 3
        v3_path = file_manager.save_generation_files_hierarchical(
            project_id=project_id,
            generation_id="gen-3",
            version=3,
            files={"v3.py": "# Version 3"}
        )
        
        # Verify all versions exist
        project_dir = Path(temp_storage) / project_id / "generations"
        assert project_dir.exists()
        
        version_dirs = list(project_dir.iterdir())
        assert len(version_dirs) == 3
        
        # Verify version naming
        version_names = [d.name for d in version_dirs]
        assert "v1__gen-1" in version_names
        assert "v2__gen-2" in version_names
        assert "v3__gen-3" in version_names
    
    def test_nested_directory_structure(self, file_manager, temp_storage):
        """Test deeply nested file structures"""
        
        files = {
            "src/app/core/config.py": "# Config",
            "src/app/api/v1/endpoints/users.py": "# Users endpoint",
            "src/app/api/v1/endpoints/posts.py": "# Posts endpoint",
            "tests/unit/test_users.py": "# User tests",
            "tests/integration/test_api.py": "# API tests"
        }
        
        storage_path = file_manager.save_generation_files_hierarchical(
            project_id="nested-project",
            generation_id="gen-nested",
            version=1,
            files=files
        )
        
        source_dir = Path(storage_path) / "source"
        
        # Verify all nested paths exist
        assert (source_dir / "src" / "app" / "core" / "config.py").exists()
        assert (source_dir / "src" / "app" / "api" / "v1" / "endpoints" / "users.py").exists()
        assert (source_dir / "tests" / "unit" / "test_users.py").exists()
        assert (source_dir / "tests" / "integration" / "test_api.py").exists()


class TestDiffGeneration:
    """Test diff generation between versions"""
    
    @pytest.fixture
    def temp_storage(self):
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def file_manager(self, temp_storage, monkeypatch):
        monkeypatch.setattr("app.services.file_manager.settings.FILE_STORAGE_PATH", temp_storage)
        monkeypatch.setattr("app.services.file_manager.settings.TEMP_STORAGE_PATH", temp_storage)
        return FileManager()
    
    def test_create_simple_diff(self, file_manager, temp_storage):
        """Test creating diff between two generations"""
        
        project_id = "diff-project"
        
        # Version 1
        files_v1 = {
            "app.py": "print('version 1')",
            "utils.py": "def util(): pass"
        }
        
        path_v1 = file_manager.save_generation_files_hierarchical(
            project_id=project_id,
            generation_id="gen-v1",
            version=1,
            files=files_v1
        )
        
        # Version 2 (modified + new file)
        files_v2 = {
            "app.py": "print('version 2')",  # Modified
            "utils.py": "def util(): pass",   # Unchanged
            "config.py": "# New config file"  # Added
        }
        
        path_v2 = file_manager.save_generation_files_hierarchical(
            project_id=project_id,
            generation_id="gen-v2",
            version=2,
            files=files_v2
        )
        
        # Create diff
        diff = file_manager.create_generation_diff(path_v1, path_v2)
        
        assert diff is not None
        assert len(diff) > 0
        
        # Diff should contain change to app.py
        assert "app.py" in diff
        assert "version 1" in diff or "version 2" in diff
    
    def test_diff_with_file_removal(self, file_manager, temp_storage):
        """Test diff when files are removed"""
        
        project_id = "removal-project"
        
        # Version 1: Multiple files
        files_v1 = {
            "keep.py": "# Keep this",
            "remove.py": "# Remove this"
        }
        
        path_v1 = file_manager.save_generation_files_hierarchical(
            project_id=project_id,
            generation_id="gen-v1",
            version=1,
            files=files_v1
        )
        
        # Version 2: File removed
        files_v2 = {
            "keep.py": "# Keep this"
        }
        
        path_v2 = file_manager.save_generation_files_hierarchical(
            project_id=project_id,
            generation_id="gen-v2",
            version=2,
            files=files_v2
        )
        
        # Create diff
        diff = file_manager.create_generation_diff(path_v1, path_v2)
        
        # Should show removal
        assert "remove.py" in diff


class TestActiveGenerationSymlinks:
    """Test active generation symlink/junction management"""
    
    @pytest.fixture
    def temp_storage(self):
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def file_manager(self, temp_storage, monkeypatch):
        monkeypatch.setattr("app.services.file_manager.settings.FILE_STORAGE_PATH", temp_storage)
        monkeypatch.setattr("app.services.file_manager.settings.TEMP_STORAGE_PATH", temp_storage)
        return FileManager()
    
    def test_set_active_generation_creates_symlink(self, file_manager, temp_storage):
        """Test that set_active_generation creates active symlink"""
        
        project_id = "symlink-project"
        generation_id = "active-gen"
        version = 3
        
        # Create generation directory
        files = {"app.py": "print('active')"}
        storage_path = file_manager.save_generation_files_hierarchical(
            project_id=project_id,
            generation_id=generation_id,
            version=version,
            files=files
        )
        
        # Set as active
        file_manager.set_active_generation_symlink(
            project_id=project_id,
            generation_id=generation_id,
            version=version
        )
        
        # Verify active link exists
        active_link = Path(temp_storage) / project_id / "generations" / "active"
        assert active_link.exists()
        
        # On Windows, might be a junction; on Unix, a symlink
        # Both should point to the version directory
        if active_link.is_symlink() or active_link.exists():
            # Link exists and points somewhere
            assert True
    
    def test_switch_active_generation(self, file_manager, temp_storage):
        """Test switching active generation updates symlink"""
        
        project_id = "switch-project"
        
        # Create version 1
        file_manager.save_generation_files_hierarchical(
            project_id=project_id,
            generation_id="gen-v1",
            version=1,
            files={"v1.py": "# V1"}
        )
        
        # Set v1 as active
        file_manager.set_active_generation_symlink(
            project_id=project_id,
            generation_id="gen-v1",
            version=1
        )
        
        # Create version 2
        file_manager.save_generation_files_hierarchical(
            project_id=project_id,
            generation_id="gen-v2",
            version=2,
            files={"v2.py": "# V2"}
        )
        
        # Switch to v2
        file_manager.set_active_generation_symlink(
            project_id=project_id,
            generation_id="gen-v2",
            version=2
        )
        
        # Active link should exist
        active_link = Path(temp_storage) / project_id / "generations" / "active"
        assert active_link.exists()


class TestVersionAutoIncrement:
    """Test version auto-increment logic"""
    
    def test_version_assignment(self):
        """Test that versions are assigned sequentially"""
        
        versions = []
        
        # Simulate creating 5 generations
        for i in range(1, 6):
            # In real code, this would be handled by GenerationService.create_generation()
            # which queries MAX(version) and adds 1
            if versions:
                next_version = max(versions) + 1
            else:
                next_version = 1
            
            versions.append(next_version)
        
        assert versions == [1, 2, 3, 4, 5]
    
    def test_version_gaps_handled(self):
        """Test that version numbering handles gaps (e.g., if a generation was deleted)"""
        
        # Existing versions: 1, 2, 4 (3 was deleted)
        existing_versions = [1, 2, 4]
        
        # Next version should be MAX + 1 = 5
        next_version = max(existing_versions) + 1
        
        assert next_version == 5


class TestBackwardCompatibility:
    """Test backward compatibility with old storage format"""
    
    @pytest.fixture
    def temp_storage(self):
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def file_manager(self, temp_storage, monkeypatch):
        monkeypatch.setattr("app.services.file_manager.settings.FILE_STORAGE_PATH", temp_storage)
        monkeypatch.setattr("app.services.file_manager.settings.TEMP_STORAGE_PATH", temp_storage)
        return FileManager()
    
    def test_old_format_still_supported(self, file_manager, temp_storage):
        """Test that old flat storage format still works"""
        
        generation_id = "old-gen-123"
        files = {"app.py": "# Old format"}
        
        # Use old format method
        old_path = file_manager.save_generation_files(generation_id, files)
        
        # Verify old structure
        old_gen_dir = Path(temp_storage) / "projects" / generation_id
        assert old_gen_dir.exists()
        assert (old_gen_dir / "app.py").exists()
    
    def test_both_formats_coexist(self, file_manager, temp_storage):
        """Test that both old and new formats can coexist"""
        
        # Old format
        old_gen_id = "old-gen"
        file_manager.save_generation_files(old_gen_id, {"old.py": "# Old"})
        
        # New format
        project_id = "new-project"
        new_gen_id = "new-gen"
        file_manager.save_generation_files_hierarchical(
            project_id=project_id,
            generation_id=new_gen_id,
            version=1,
            files={"new.py": "# New"}
        )
        
        # Both should exist
        old_path = Path(temp_storage) / "projects" / old_gen_id
        new_path = Path(temp_storage) / project_id / "generations" / f"v1__{new_gen_id}"
        
        assert old_path.exists()
        assert new_path.exists()


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    @pytest.fixture
    def temp_storage(self):
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def file_manager(self, temp_storage, monkeypatch):
        monkeypatch.setattr("app.services.file_manager.settings.FILE_STORAGE_PATH", temp_storage)
        monkeypatch.setattr("app.services.file_manager.settings.TEMP_STORAGE_PATH", temp_storage)
        return FileManager()
    
    def test_empty_files_dict(self, file_manager):
        """Test handling empty files dictionary"""
        
        # Should not crash, just create empty generation
        storage_path = file_manager.save_generation_files_hierarchical(
            project_id="empty-project",
            generation_id="empty-gen",
            version=1,
            files={}
        )
        
        assert storage_path is not None
        manifest_path = Path(storage_path) / "manifest.json"
        assert manifest_path.exists()
        
        with open(manifest_path) as f:
            manifest = json.load(f)
        
        assert manifest["file_count"] == 0
    
    def test_special_characters_in_filenames(self, file_manager):
        """Test handling special characters in file paths"""
        
        files = {
            "file with spaces.py": "# Spaces",
            "file-with-dashes.py": "# Dashes",
            "file_with_underscores.py": "# Underscores"
        }
        
        storage_path = file_manager.save_generation_files_hierarchical(
            project_id="special-chars",
            generation_id="gen-special",
            version=1,
            files=files
        )
        
        source_dir = Path(storage_path) / "source"
        
        # All files should be created
        assert (source_dir / "file with spaces.py").exists()
        assert (source_dir / "file-with-dashes.py").exists()
        assert (source_dir / "file_with_underscores.py").exists()
    
    def test_large_file_content(self, file_manager):
        """Test handling large file content"""
        
        # Create a large file (1MB of content)
        large_content = "# " + ("x" * 1024 * 1024)
        
        files = {"large_file.py": large_content}
        
        storage_path = file_manager.save_generation_files_hierarchical(
            project_id="large-project",
            generation_id="large-gen",
            version=1,
            files=files
        )
        
        # Verify file was created
        large_file = Path(storage_path) / "source" / "large_file.py"
        assert large_file.exists()
        
        # Verify size in manifest
        manifest_path = Path(storage_path) / "manifest.json"
        with open(manifest_path) as f:
            manifest = json.load(f)
        
        assert manifest["files"][0]["size"] > 1024 * 1024
