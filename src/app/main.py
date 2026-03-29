from fastapi import FastAPI
from app.api.endpoints import router as orchestrator_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Agent Orchestrator",
        description="Microservice for orchestrating AI agents using Temporal and LangGraph.",
        version="0.1.0",
    )

    app.include_router(orchestrator_router)

    return app


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
