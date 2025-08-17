"""
Lightweight code reviewer stub for tests.
"""

from typing import Dict, Any


class CodeReviewer:
	async def review(self, files: Dict[str, str]) -> Dict[str, Any]:
		return {
			"issues": [],
			"suggestions": [],
			"security_score": 0.9,
			"maintainability_score": 0.9,
			"performance_score": 0.9,
			"overall_score": 0.9,
		}


code_reviewer = CodeReviewer()
