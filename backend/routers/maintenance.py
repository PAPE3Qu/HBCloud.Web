# Deprecated maintenance API module.
# The clear-file-detail functionality has been moved to tools scripts
# for manual invocation and is no longer exposed as an HTTP endpoint.

from fastapi import APIRouter

router = APIRouter()

# No public routes here. Use tools/delete_file_detail_index.py or similar
# scripts in the tools directory for maintenance operations.
