from dataclasses import dataclass


@dataclass
class GoogleUser:
    id: str
    email: str
    name: str
    picture: str
