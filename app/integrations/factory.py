from app.core.config import get_settings
from app.integrations.climate_provider import ClimateProvider
from app.integrations.mock_provider import MockProvider
from app.integrations.nasa_power import NasaPowerProvider


def build_provider() -> ClimateProvider:
    s = get_settings()
    if s.CLIMATE_PROVIDER == "mock":
        return MockProvider()
    return NasaPowerProvider(s.NASA_POWER_BASE_URL, s.NASA_TIMEOUT_S, s.NASA_RETRIES)
