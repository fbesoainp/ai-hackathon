from fastapi import APIRouter

from routers import account, partner, restaurant, token

ROUTERS: list[APIRouter] = [partner.router, restaurant.router, account.router, token.router]
