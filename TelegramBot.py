from telegram.ext import ApplicationBuilder, CommandHandler, filters, CallbackQueryHandler
from telegram import Update

class TelegramBot():
    __slots__ = ["token", "online", "app", "handlers"]

    def __init__(self, token: str) -> None:
        self.token = token
        self.online = False
        self.handlers = []


    def on(self) -> bool:
        if self.online:
            print("Bot is already online")

            return False
        
        else:            
            self.app = ApplicationBuilder().token(self.token).build()

            for handler in self.handlers:
                self.app.add_handler(handler)
            self.app.run_polling()

            return True
        

    def off(self) -> bool:
        if self.online:
            self.app.shutdown()
            return True        
        else:
            return False
        

    def AddCommandHandler(self, command: str, filters=None):
        def decorator(func):
            async def wrapper(update, context, *args, **kwargs):
                return await func(update, context, *args, **kwargs)

            handler = CommandHandler(command=command, callback=wrapper, filters=filters)
            self.handlers.append(handler)
            return handler

        return decorator


    def AddCallbackQueryHandler(self, command: str, filters=None):
        def decorator(func):
            async def wrapper(update, context, *args, **kwargs):
                return await func(update, context, *args, **kwargs)

            handler = CallbackQueryHandler(command=command, callback=wrapper, filters=filters)
            self.handlers.append(handler)
            return handler

        return decorator