"""
App domain package.

Mounted only in app mode (``trove start``). Contains the auth-gated admin
panel endpoints, session cookie management, and capability flags. Sub-routers
for Gems and the document library are included via backend.app.router.
"""
