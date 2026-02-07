import utils.services.dbutils as dbutils
from datetime import datetime
import db
from functools import partial
import asyncio
from languages import l

async def reminder(self, ctx, choice : str|None = None):
        info = await dbutils.get_user_info(ctx.author.id)
        if (choice != None):
            choice = choice.lower().strip()
            if (choice == l.text("enable")): toggle = True
            elif (choice == l.text("disable")): toggle = False
            else: 
                await ctx.send(l.text("invalid_choice"))
                return
        else:
            toggle = not info["reminder"]
        
        if (toggle != info["reminder"]): await db.execute("UPDATE users SET reminder = %s WHERE id = %s", (toggle, ctx.author.id))
        if toggle == True:
            now = datetime.now()
            if (info["reminder_at"] is not None and info["reminder_at"] > now): 
                task = asyncio.create_task(self.schedule_harvest_reminder(ctx.author.id, info["reminder_at"], info["last_harvest_channel"]))
                task.add_done_callback(partial(lambda uid, t: self.pending_reminders.pop(uid, None), ctx.author.id))
                self.pending_reminders[ctx.author.id] = task
        else:
            task = self.pending_reminders.pop(ctx.author.id, None)
            if task: task.cancel()

        option = l.text("enabled") if toggle == True else l.text("disabled")
        await ctx.send(l.text("reminder", "changed", option=option))