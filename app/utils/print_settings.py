from app.core.config import settings

print("ENV:", settings.throttle_env)
print("REQUIRE_API_KEY:", settings.throttle_require_api_key,
      type(settings.throttle_require_api_key))
print("API_KEYS_RAW:", settings.throttle_api_keys)
print("API_KEY_SET:", settings.api_key_set)
