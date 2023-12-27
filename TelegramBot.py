from telegram.ext import ApplicationBuilder, CommandHandler, filters, CallbackQueryHandler
from telegram import Update

class TelegramBot():
    '''
    A class that creates a bot for telegram, with the ability to add handlers and then launch
    '''
    __slots__ = ["token", "online", "app"]

    def __init__(self, token: str) -> None:
        self.token = token
        self.online = False        
        self.app = ApplicationBuilder().token(self.token).build()


    def on(self) -> bool:
        if self.online:
            print("Bot is already online")
            return False
        
        else:
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
            self.app.add_handler(handler)
            return handler

        return decorator


    def AddCallbackQueryHandler(self, pattern=None):
        def decorator(func):
            async def wrapper(update, context, *args, **kwargs):
                return await func(update, context, *args, **kwargs)

            handler = CallbackQueryHandler(callback=wrapper, pattern=pattern)
            self.handlers.append(handler)
            return handler

        return decorator
    
    
    def AddJobQuery(self, repeating=False, first=None, interval=86400.0):
        def decorator(func):
            async def wrapper(context, *args, **kwargs):
                return await func(context, *args, **kwargs)
            
            if repeating:
                self.app.job_queue.run_repeating(wrapper, interval=interval, first=first)
            else:
                self.app.job_queue.run_once(wrapper, when=first)
            return wrapper

        return decorator