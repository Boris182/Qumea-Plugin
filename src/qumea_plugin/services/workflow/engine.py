from typing import Protocol, Any

class Stage(Protocol):
    async def run(self, ctx, event: dict) -> dict:
        ...

class WorkflowEngine:
    def __init__(self, stages: list[Stage]):
        self.stages = stages

    async def handle_event(self, ctx, event: dict) -> None:
        data = event
        for stage in self.stages:
            data = await stage.run(ctx, data)