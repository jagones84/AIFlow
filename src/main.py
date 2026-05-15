import asyncio
import json
import os
from typing import List
from dotenv import load_dotenv

from src.models.node_models import FlowProjectData, NodeData, Connection
from src.logic.node_executor import NodeExecutor
from src.logic.flow_orchestrator import FlowOrchestrator
from src.utils.managers import LogManager

# Load environment variables from .env file
load_dotenv()

class FlowApp:
    def __init__(self, project_data: FlowProjectData):
        self.project_data = project_data
        self.node_executor = NodeExecutor()
        
        self.orchestrator = FlowOrchestrator(
            node_executor=self.node_executor,
            get_nodes=self.get_nodes,
            get_connections=self.get_connections,
            update_nodes=self.update_nodes,
            update_connections=self.update_connections,
            load_flow=self.load_flow
        )

    def get_nodes(self) -> List[NodeData]:
        return self.project_data.nodes

    def get_connections(self) -> List[Connection]:
        return self.project_data.connections

    def update_nodes(self, nodes: List[NodeData]):
        self.project_data.nodes = nodes

    def update_connections(self, connections: List[Connection]):
        self.project_data.connections = connections

    def load_flow(self, flow_id: str) -> FlowProjectData:
        # Mock load flow
        return None

    async def run(self):
        LogManager.info("Main", "Starting FlowApp")
        await self.orchestrator.start_flow()
        
        while self.orchestrator.is_flow_running:
            await asyncio.sleep(1)
            
        LogManager.info("Main", "FlowApp finished")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="AI Flow Engine")
    parser.add_argument("--config", type=str, default="config/workflow.json", help="Path to workflow config")
    args = parser.parse_args()
    
    if os.path.exists(args.config):
        with open(args.config, "r", encoding="utf-8") as f:
            data = json.load(f)
            project = FlowProjectData(**data)
    else:
        # Fallback to an empty project
        project = FlowProjectData(name="Empty", nodes=[], connections=[])
        
    app = FlowApp(project)
    asyncio.run(app.run())
