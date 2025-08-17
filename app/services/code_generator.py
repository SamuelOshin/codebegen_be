"""
Lightweight code generator service stub used during tests and as a fallback.
Provides a minimal async API compatible with callers.
"""

from typing import Dict, Any


class CodeGenerator:
	async def generate(self, prompt: str, schema: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, str]:
		"""Return a minimal but valid FastAPI project structure."""
		return {
			"app/main.py": (
				"from fastapi import FastAPI\n"
				"app = FastAPI(title='Generated API')\n\n"
				"@app.get('/')\n"
				"async def root():\n"
				"    return {'message': 'ok'}\n"
			),
			"README.md": "# Generated API\nThis is a stub generation.",
		}


# Module-level instance for import convenience
code_generator = CodeGenerator()
