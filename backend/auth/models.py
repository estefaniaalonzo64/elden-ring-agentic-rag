from pydantic import BaseModel


class UserRecord(BaseModel):
    user_id: str
    username: str
    password_hash: str
    password_salt: str
