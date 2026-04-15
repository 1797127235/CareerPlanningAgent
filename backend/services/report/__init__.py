"""Report service package."""
from backend.services.report.pipeline import (  # noqa: F401
    generate_report,
    polish_narrative,
)
from backend.services.report.loaders import reload_static  # noqa: F401
