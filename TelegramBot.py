from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler

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
        

    @staticmethod
    def AddCommandHandler(command: str, filters=None):
        def decorator(func):
            async def wrapper(update, context, *args, **kwargs):
                return await func(update, context, *args, **kwargs)

            handler = CommandHandler(command=command, callback=wrapper, filters=filters)
            TelegramBot.handlers.append(handler)

            return handler

        return decorator


    @staticmethod
    def AddCallbackQueryHandler(pattern=None):
        def decorator(func):
            async def wrapper(update, context, *args, **kwargs):
                return await func(update, context, *args, **kwargs)

            handler = CallbackQueryHandler(callback=wrapper, pattern=pattern)
            TelegramBot.handlers.append(handler)

            return handler

        return decorator
    

    @staticmethod
    def AddJobQuery(repeating=False, first=None, interval=86400.0):
        def decorator(func):
            async def wrapper(context, *args, **kwargs):
                return await func(context, *args, **kwargs)
            
            TelegramBot.job_queue.append({"repeating": repeating, "func": wrapper, "interval": interval, "first": first})

            return wrapper

        return decorator
