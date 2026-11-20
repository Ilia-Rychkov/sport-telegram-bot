import os
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlmodel import Session

from database.database import engine
from backend.services.profile_service import ProfileService
from backend.services.workout_service import WorkoutService
from backend.services.gemini_provider import GeminiProvider
from backend.services.nutrition_service import NutritionService
from backend.services.workout_parser_service import WorkoutParserService

WORKER_URL = "https://geminishka.weity-deadliner.workers.dev"
MODEL = "gemini-3.5-flash-lite"


class DatabaseMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        with Session(engine) as session:
            profile_service = ProfileService(session)
            workout_service = WorkoutService(session)

            # ВОТ ЗДЕСЬ ИСПРАВЬ:
            ai_provider = GeminiProvider(
                api_key=os.getenv("AI_API_KEY"),
                base_url=WORKER_URL,
                model=MODEL
            )
            nutrition_service = NutritionService(ai_provider)
            workout_parser = WorkoutParserService(ai_provider)

            data["profile_service"] = profile_service
            data["workout_service"] = workout_service
            data["nutrition_service"] = nutrition_service
            data["workout_parser"] = workout_parser

            return await handler(event, data)