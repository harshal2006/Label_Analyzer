from jose import jwt
import time
from uuid import uuid4

secret = "b0JiVaHE2HoN/cCM9EwqhRoEFiVkZJxsyuxMCaFEdgmYdKw6DqTNzC+oApsvs6p/rKwMUMezKuAz9iGhgFRvHA=="
user_id = str(uuid4())
payload = {
    "aud": "authenticated",
    "exp": int(time.time()) + 3600,
    "sub": user_id,
    "role": "authenticated"
}
token = jwt.encode(payload, secret, algorithm="HS256")
print(token)
