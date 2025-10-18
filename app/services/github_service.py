"""
GitHub integration service for exporting generated projects.
Handles repository creation, file uploads, and PR management.
"""

import asyncio
import base64
from loguru import logger
from typing import Dict, List, Optional, Tuple
from datetime import datetime

import httpx
from fastapi import HTTPException

from app.core.config import settings
from app.services.file_manager import file_manager

logger = logger


class GitHubService:
    """Handles GitHub API interactions for project export."""
    
    def __init__(self):
        self.base_url = "https://api.github.com"
        self.timeout = 30
    
    async def create_repository(
        self,
        access_token: str,
        repo_name: str,
        description: str = "",
        private: bool = False
    ) -> Dict[str, any]:
        """
        Create a new GitHub repository.
        
        Args:
            access_token: GitHub access token
            repo_name: Name of the repository
            description: Repository description
            private: Whether the repository should be private
            
        Returns:
            Repository information from GitHub API
        """
        try:
            headers = {
                "Authorization": f"token {access_token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "CodebeGen/1.0"
            }
            
            data = {
                "name": repo_name,
                "description": description,
                "private": private,
                "auto_init": True,
                "gitignore_template": "Python"
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/user/repos",
                    headers=headers,
                    json=data
                )
                
                if response.status_code == 201:
                    repo_data = response.json()
                    logger.info(f"Created GitHub repository: {repo_data['full_name']}")
                    return repo_data
                elif response.status_code == 422:
                    # Repository already exists
                    error_data = response.json()
                    if "name already exists" in str(error_data):
                        raise HTTPException(
                            status_code=409,
                            detail=f"Repository '{repo_name}' already exists"
                        )
                    raise HTTPException(status_code=422, detail=error_data)
                else:
                    response.raise_for_status()
                    
        except httpx.HTTPStatusError as e:
            logger.error(f"GitHub API error: {e.response.status_code} - {e.response.text}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"GitHub API error: {e.response.text}"
            )
        except Exception as e:
            logger.error(f"Error creating repository: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create repository: {str(e)}"
            )
    
    async def upload_files_to_repo(
        self,
        access_token: str,
        owner: str,
        repo_name: str,
        generation_id: str,
        commit_message: str = "Initial commit from CodebeGen"
    ) -> bool:
        """
        Upload generated project files to a GitHub repository.
        
        Args:
            access_token: GitHub access token
            owner: Repository owner (username or organization)
            repo_name: Repository name
            generation_id: Generation ID to get files from
            commit_message: Commit message
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get project files
            files = await file_manager.get_project_files(generation_id)
            if not files:
                logger.error(f"No files found for generation {generation_id}")
                return False
            
            headers = {
                "Authorization": f"token {access_token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "CodebeGen/1.0"
            }
            
            # Get the default branch (usually main or master)
            branch = await self._get_default_branch(access_token, owner, repo_name)
            
            # Get the latest commit SHA
            latest_commit_sha = await self._get_latest_commit_sha(
                access_token, owner, repo_name, branch
            )
            
            # Create a tree with all files
            tree_items = []
            for file_path, content in files.items():
                # Skip certain files that shouldn't be in the repo
                if file_path in ['.env', '.env.local', '__pycache__']:
                    continue
                
                # Create blob for file content
                blob_sha = await self._create_blob(
                    access_token, owner, repo_name, content
                )
                
                tree_items.append({
                    "path": file_path,
                    "mode": "100644",
                    "type": "blob",
                    "sha": blob_sha
                })
            
            # Create tree
            tree_sha = await self._create_tree(
                access_token, owner, repo_name, tree_items, latest_commit_sha
            )
            
            # Create commit
            commit_sha = await self._create_commit(
                access_token, owner, repo_name, commit_message, tree_sha, latest_commit_sha
            )
            
            # Update branch reference
            await self._update_ref(
                access_token, owner, repo_name, branch, commit_sha
            )
            
            logger.info(f"Successfully uploaded files to {owner}/{repo_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error uploading files to repo: {e}")
            return False
    
    async def create_pull_request(
        self,
        access_token: str,
        owner: str,
        repo_name: str,
        generation_id: str,
        branch_name: str = None,
        title: str = "CodebeGen Generated Code",
        description: str = "Automatically generated code from CodebeGen"
    ) -> Optional[Dict[str, any]]:
        """
        Create a pull request with generated code.
        
        Args:
            access_token: GitHub access token
            owner: Repository owner
            repo_name: Repository name
            generation_id: Generation ID to get files from
            branch_name: Name of the new branch (auto-generated if None)
            title: PR title
            description: PR description
            
        Returns:
            Pull request data or None if failed
        """
        try:
            if not branch_name:
                timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                branch_name = f"codebegen-{timestamp}"
            
            headers = {
                "Authorization": f"token {access_token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "CodebeGen/1.0"
            }
            
            # Get the default branch
            default_branch = await self._get_default_branch(access_token, owner, repo_name)
            
            # Create new branch
            await self._create_branch(
                access_token, owner, repo_name, branch_name, default_branch
            )
            
            # Upload files to the new branch
            files = await file_manager.get_project_files(generation_id)
            if not files:
                return None
            
            # Upload each file to the branch
            for file_path, content in files.items():
                if file_path in ['.env', '.env.local', '__pycache__']:
                    continue
                    
                await self._create_or_update_file(
                    access_token, owner, repo_name, file_path, 
                    content, f"Add {file_path}", branch_name
                )
            
            # Create pull request
            pr_data = {
                "title": title,
                "body": description,
                "head": branch_name,
                "base": default_branch
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/repos/{owner}/{repo_name}/pulls",
                    headers=headers,
                    json=pr_data
                )
                
                if response.status_code == 201:
                    pr_info = response.json()
                    logger.info(f"Created PR: {pr_info['html_url']}")
                    return pr_info
                else:
                    logger.error(f"Failed to create PR: {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error creating pull request: {e}")
            return None
    
    async def get_user_repos(
        self,
        access_token: str,
        per_page: int = 30
    ) -> List[Dict[str, any]]:
        """
        Get user's repositories.
        
        Args:
            access_token: GitHub access token
            per_page: Number of repos per page
            
        Returns:
            List of repository information
        """
        try:
            headers = {
                "Authorization": f"token {access_token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "CodebeGen/1.0"
            }
            
            params = {
                "per_page": per_page,
                "sort": "updated",
                "direction": "desc"
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/user/repos",
                    headers=headers,
                    params=params
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Failed to get user repos: {response.text}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error getting user repos: {e}")
            return []
    
    async def _get_default_branch(
        self, access_token: str, owner: str, repo_name: str
    ) -> str:
        """Get the default branch of a repository."""
        headers = {
            "Authorization": f"token {access_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/repos/{owner}/{repo_name}",
                headers=headers
            )
            
            if response.status_code == 200:
                repo_data = response.json()
                return repo_data["default_branch"]
            else:
                return "main"  # Default fallback
    
    async def _get_latest_commit_sha(
        self, access_token: str, owner: str, repo_name: str, branch: str
    ) -> str:
        """Get the SHA of the latest commit on a branch."""
        headers = {
            "Authorization": f"token {access_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/repos/{owner}/{repo_name}/git/refs/heads/{branch}",
                headers=headers
            )
            
            if response.status_code == 200:
                ref_data = response.json()
                return ref_data["object"]["sha"]
            else:
                raise Exception(f"Failed to get latest commit SHA: {response.text}")
    
    async def _create_blob(
        self, access_token: str, owner: str, repo_name: str, content: str
    ) -> str:
        """Create a blob with file content."""
        headers = {
            "Authorization": f"token {access_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        # Encode content as base64
        content_encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        
        data = {
            "content": content_encoded,
            "encoding": "base64"
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/repos/{owner}/{repo_name}/git/blobs",
                headers=headers,
                json=data
            )
            
            if response.status_code == 201:
                blob_data = response.json()
                return blob_data["sha"]
            else:
                raise Exception(f"Failed to create blob: {response.text}")
    
    async def _create_tree(
        self, access_token: str, owner: str, repo_name: str, 
        tree_items: List[Dict], base_tree_sha: str
    ) -> str:
        """Create a git tree."""
        headers = {
            "Authorization": f"token {access_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        data = {
            "tree": tree_items,
            "base_tree": base_tree_sha
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/repos/{owner}/{repo_name}/git/trees",
                headers=headers,
                json=data
            )
            
            if response.status_code == 201:
                tree_data = response.json()
                return tree_data["sha"]
            else:
                raise Exception(f"Failed to create tree: {response.text}")
    
    async def _create_commit(
        self, access_token: str, owner: str, repo_name: str,
        message: str, tree_sha: str, parent_sha: str
    ) -> str:
        """Create a commit."""
        headers = {
            "Authorization": f"token {access_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        data = {
            "message": message,
            "tree": tree_sha,
            "parents": [parent_sha]
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/repos/{owner}/{repo_name}/git/commits",
                headers=headers,
                json=data
            )
            
            if response.status_code == 201:
                commit_data = response.json()
                return commit_data["sha"]
            else:
                raise Exception(f"Failed to create commit: {response.text}")
    
    async def _update_ref(
        self, access_token: str, owner: str, repo_name: str,
        branch: str, commit_sha: str
    ) -> bool:
        """Update a branch reference."""
        headers = {
            "Authorization": f"token {access_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        data = {
            "sha": commit_sha,
            "force": True
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.patch(
                f"{self.base_url}/repos/{owner}/{repo_name}/git/refs/heads/{branch}",
                headers=headers,
                json=data
            )
            
            return response.status_code == 200
    
    async def _create_branch(
        self, access_token: str, owner: str, repo_name: str,
        branch_name: str, source_branch: str
    ) -> bool:
        """Create a new branch."""
        # Get source branch SHA
        source_sha = await self._get_latest_commit_sha(
            access_token, owner, repo_name, source_branch
        )
        
        headers = {
            "Authorization": f"token {access_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        data = {
            "ref": f"refs/heads/{branch_name}",
            "sha": source_sha
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/repos/{owner}/{repo_name}/git/refs",
                headers=headers,
                json=data
            )
            
            return response.status_code == 201
    
    async def _create_or_update_file(
        self, access_token: str, owner: str, repo_name: str,
        file_path: str, content: str, message: str, branch: str
    ) -> bool:
        """Create or update a file in the repository."""
        headers = {
            "Authorization": f"token {access_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        # Encode content as base64
        content_encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        
        data = {
            "message": message,
            "content": content_encoded,
            "branch": branch
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.put(
                f"{self.base_url}/repos/{owner}/{repo_name}/contents/{file_path}",
                headers=headers,
                json=data
            )
            
            return response.status_code in [200, 201]


# Global instance
github_service = GitHubService()