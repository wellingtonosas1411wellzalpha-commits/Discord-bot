from core import *

@bot.tree.command(name="profile", description="See every stat for a player: economy, level, job, pet, marriage, achievements, inventory")
@app_commands.describe(member="The member to look up (defaults to you)")
async def profile(interaction: discord.Interaction, member: discord.Member = None):
    await interaction.response.defer()
    member = member or interaction.user
    try:
        embed = build_profile_embed(member)
    except Exception as e:
        print(f"profile command failed: {e}")
        await interaction.followup.send("❌ Something went wrong building that profile. Try again in a moment.")
        return
    await interaction.followup.send(embed=embed)


@bot.command(name="profile")
async def profile_prefix(ctx: commands.Context, member: discord.Member = None):
    member = member or ctx.author
    try:
        embed = build_profile_embed(member)
    except Exception as e:
        print(f"profile command failed: {e}")
        await ctx.reply("❌ Something went wrong building that profile. Try again in a moment.")
        return
    await ctx.reply(embed=embed)

