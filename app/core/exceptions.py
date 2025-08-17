from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR


def setup_exception_handlers(app: FastAPI) -> None:
	"""Register minimal exception handlers used by the application.

	This keeps startup importing safe for dev and tests. Extend handlers as needed.
	"""

	@app.exception_handler(HTTPException)
	async def http_exception_handler(request: Request, exc: HTTPException):
		return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

	@app.exception_handler(Exception)
	async def generic_exception_handler(request: Request, exc: Exception):
		# In production, log the exception with traceback and return a generic message.
		return JSONResponse(status_code=HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": "Internal server error"})

