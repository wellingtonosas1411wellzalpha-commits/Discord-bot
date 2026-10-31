from core import *

@bot.tree.command(name="8ball", description="Ask the magic 8-ball a question")
@app_commands.describe(question="Your yes/no question")
async def eight_ball(interaction: discord.Interaction, question: str):
    answer = get_8ball_answer()
    await interaction.response.send_message(
        f"🎱 **Q:** {question}\n**A:** {answer}"
    )


@bot.command(name="8ball")
async def eight_ball_prefix(ctx: commands.Context, *, question: str):
    answer = get_8ball_answer()
    await ctx.reply(f"🎱 **Q:** {question}\n**A:** {answer}")

