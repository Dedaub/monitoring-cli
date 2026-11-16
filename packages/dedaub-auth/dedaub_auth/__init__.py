"""Login and credentials shared by the Dedaub CLIs.

``dedaub_auth.auth`` does the Keycloak device-flow login and the token
refresh; ``dedaub_auth.config`` reads and writes the credentials file.
dedaub-monitoring and the other Dedaub CLIs use them, so one login serves
them all.
"""
