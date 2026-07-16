Configuration
~~~~~~~~~~~~~

1. Go to Settings > TMS > Configuration
2. Choose your preferred distance provider:

   - **Haversine (Line)**: Fast, no external dependencies, but less accurate
   - **OSRM (Roads)**: Real road distances, requires OSRM server
   - **Google Maps**: Most accurate, requires API key and billing

3. Configure additional options:

   - **OSRM Server URL**: Custom OSRM server for self-hosted installations
   - **Enable Fallback**: Automatically fall back to Haversine if OSRM fails
