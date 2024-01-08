from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler
from functools import wraps

class TelegramBot():
    '''
    A class that creates a bot for telegram, with the ability to add handlers and then launch
    '''
    __slots__ = ["token", "online", "app"]
    handlers = []
    job_queue = []

    def __init__(self, token: str) -> None:
        self.token = token
        self.online = False        
        self.app = ApplicationBuilder().token(self.token).build()


    def on(self) -> bool:
        if self.online:
            print("Bot is already online")
            return False
        
        else:
            self.app.add_handlers(TelegramBot.handlers)

            for job in TelegramBot.job_queue:
                if job["repeating"]:
                    self.app.job_queue.run_repeating(callback=job["func"], interval=job["interval"], first=job["first"])
                else:
                    self.app.job_queue.run_once(callback=job["func"], when=job["first"])

            self.app.run_polling()
            return True
        

    def off(self) -> bool:
        if self.online:
            self.app.shutdown()
            return True        
        else:
            return False
        

    @classmethod
    def AddCommandHandler(cls, command: str, filters=None):
        def decorator(func):
            async def wrapper(update, context, *args, **kwargs):
                return await func(update, context, *args, **kwargs)

            handler = CommandHandler(command=command, callback=wrapper, filters=filters)
            cls.handlers.append(handler)

            return handler

        return decorator


    @classmethod
    def AddCallbackQueryHandler(cls, pattern=None):
        def decorator(func):

            @wraps(func)
            async def wrapper(update, context, *args, **kwargs):
                return await func(update, context, *args, **kwargs)

            handler = CallbackQueryHandler(callback=wrapper, pattern=pattern)
            cls.handlers.append(handler)

            return handler

        return decorator
    

    @classmethod
    def AddJobQuery(cls, repeating=False, first=None, interval=86400.0):
        def decorator(func):
            
            @wraps(func)
            async def wrapper(context, *args, **kwargs):
                return await func(context, *args, **kwargs)
            
            cls.job_queue.append({"repeating": repeating, "func": wrapper, "interval": interval, "first": first})

            return wrapper

        return decorator
