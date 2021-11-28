import discord
from bot import ClanHelper, NickTooLong

bot = ClanHelper()


@bot.user_command(
    name='Протокол КИРКОРОВ')
async def kirkorov(ctx, member: discord.Member):
    await ctx.defer(ephemeral=True)
    if member.id == ctx.guild.owner_id:
        await ctx.respond('Пускай сам меняет свой ник, мне дискорд не разрешает')
    else:
        try:
            await bot.make_kirkorov(member)
            await ctx.respond('Ок')
        except NickTooLong as e:
            await ctx.respond('Я выбрал имя {}, но никнейм слишком длинный, меняйте на свое усмотрение'.format(e.message))


bot.startup()
