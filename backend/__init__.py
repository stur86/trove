"""
Trove backend package.

The application is a FastAPI service that runs in one of two modes:
  setup — localhost-only wizard for initial configuration (``trove setup``)
  app   — LAN-accessible task runner for daily use (``trove start``)

Entry point: backend.main — exposes create_app_setup() and create_app_app()
factory functions consumed by uvicorn and the CLI.
"""
