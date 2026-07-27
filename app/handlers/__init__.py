from app.handlers.common import router as common_router
from app.handlers.graphs import router as graph_router
from app.handlers.products import router as product_router

__all__ = ["common_router", "graph_router", "product_router"]
