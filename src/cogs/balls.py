import datetime
import json
import random
import time

import discord
from discord.ext import commands

from utils.bot_class import MyBot
from utils.cog_class import Cog


class TreeMember:
    def __init__(self, member_id: str, tagged=None):
        if tagged is None:
            tagged = []
        self.member_id = member_id
        self.tagged = tagged


def generate_tree(tree):
    population = {}
    tagged = []

    for sender_id, subtree in tree.items():
        subchilds, subpopulation = generate_tree(subtree)

        population = {**population, **subpopulation}

        tm = TreeMember(sender_id, subchilds)
        population[tm.member_id] = tm

        tagged.append(tm)

    return tagged, population


def get_tree_dict(tree):
    tagged = {}

    for sender_id, subtree in [(tm.member_id, tm.tagged) for tm in tree]:
        subchilds = get_tree_dict(subtree)
        tagged[sender_id] = subchilds

    return tagged


async def generate_visual_tree(guild, tree, indent=0):
    visual_tree = []

    for sender_id, subtree in [(tm.member_id, tm.tagged) for tm in tree]:
        try:
            sender_name = await guild.fetch_member(int(sender_id)).name
        except:
            sender_name = f"{sender_id} (left)"
        visual_tree.append("\t" * indent + f"- {sender_name}")
        visual_tree.extend(await generate_visual_tree(guild, subtree, indent=indent+1))

    return visual_tree


class Balls(Cog):
    """
    Snowball and fireball commands
    """

    def __init__(self, bot: MyBot, *args, **kwargs):
        super().__init__(bot, *args, **kwargs)
        self.bot = bot
        self.trees = {}

        with open("cache/balls.json", "r") as f:
            balls = json.load(f)

        for name, tree in balls.items():
            origins, population = generate_tree(tree)
            self.trees[name] = {"origins": origins, "population": population}

        with open("cache/balls_profiles.json", "r") as f:
            self.balls_profiles = json.load(f)

    async def get_profile(self, member_id):
        profile = self.balls_profiles.get(str(member_id), {})
        changed = False

        if profile.get('accuracy', None) is None:
            changed = True
            profile['accuracy'] = random.randint(5, 100)

        if profile.get('avoidance', None) is None:
            changed = True
            profile['avoidance'] = random.randint(99 - profile['accuracy'], 95)

        if profile.get('snow_killed_by', None) is None:
            changed = True
            profile['snow_killed_by'] = []

        if profile.get('fire_killed_by', None) is None:
            changed = True
            profile['fire_killed_by'] = []

        if profile.get('lives', None) is None:
            changed = True

            # Max 10, min 1.
            profile['lives'] = max(1, int(random.randint(100 - min(profile['accuracy'], profile['avoidance']), 100)/10))

        if profile.get('cooldown_time', None) is None:
            changed = True
            total_pct = profile['avoidance'] + profile['accuracy'] + profile['lives']
            max_cooldown = int(total_pct / 15)
            profile['cooldown_time'] = random.randint(0, max_cooldown)

        if profile.get('cooldown_time_nextok', None) is None:
            changed = True
            profile['cooldown_time_nextok'] = 0

        if changed:
            self.balls_profiles[str(member_id)] = profile
            await self.save_profiles()

        return profile

    async def save_balls(self):
        #print(self.trees)
        balls = {}
        for name, tree in self.trees.items():
            balls[name] = get_tree_dict(tree["origins"])

        with open("cache/balls.json", "w") as f:
            json.dump(balls, f, indent=4)

        self.bot.logger.info("Saved balls")

    async def save_profiles(self):
        with open("cache/balls_profiles.json", "w") as f:
            json.dump(self.balls_profiles, f, indent=4)

        self.bot.logger.info("Saved profiles")

    @commands.group(hidden=True)
    async def balls(self, ctx):
        pass

    @balls.command(hidden=True)
    async def profile(self, ctx, target:discord.Member = None):
        if target is None:
            target = ctx.author

        profile = await self.get_profile(member_id=int(target.id))

        message = [f"Your accuracy is {profile['accuracy']}%. You avoid {profile['avoidance']}% "
                   f"of balls thrown in your general direction.",
                   f"You have {profile['lives']} life(s) total."]

        if profile.get('team', None) is not None:
            message.append(f"**You are team {profile['team']}**")
        else:
            message.append(f"You have {profile['lives'] - len(profile['snow_killed_by'])} snow life(s) left, and {profile['lives'] - len(profile['fire_killed_by'])} fire life(s) left.")

        message.append(f"You can send balls every {profile['cooldown_time']} second(s)")
        await ctx.send("\n".join(message))

    @balls.command(hidden=True)
    async def tree(self, ctx, ball_type):
        if ball_type not in self.trees.keys():
            await ctx.send(f"I can't find this tree :'(. Try anything in {', '.join(self.trees.keys())}")
            return

        tree = self.trees[ball_type]["origins"]

        guild = ctx.guild

        await ctx.send("```\n" + "\n".join(await generate_visual_tree(guild, tree)) + "\n```")

    @commands.command(hidden=True)
    async def snowball(self, ctx, target: discord.Member):
        """
        Throw snowballs at people.
        """
        # if ctx.channel.id != 593075880717189123:
        #     await ctx.send("⛄️ Wrong channel. Please use #sniping-grounds", delete_after=10)
        #     return

        sender = ctx.author
        role = ctx.guild.get_role(593008022247178280)

        if role not in sender.roles:
            await ctx.send("⛄️ You don't have any snow")
            return

        sender_profile = await self.get_profile(member_id=int(sender.id))
        target_profile = await self.get_profile(member_id=int(target.id))

        sender_team = sender_profile.get("team", None)

        if sender_team == "fire":
            await ctx.send("🔥️ You don't have any more snow. Use fire instead.")
            return

        if sender_profile['cooldown_time_nextok'] > int(time.time()):
            await ctx.send("🤷️ Wait a little, you have no more balls...")
            return
        else:
            sender_profile['cooldown_time_nextok'] = int(time.time()) + sender_profile['cooldown_time']

        if not role in target.roles:
            await target.add_roles(role, reason=f"Snowballed by {sender.name}#{sender.discriminator}")
            await ctx.guild.get_channel(593011582510956544).send(f"{sender.mention} ❄️ {target.mention}")
            tm = TreeMember(str(target.id))

            self.trees["snowballs"]["population"][str(target.id)] = tm
            self.trees["snowballs"]["population"][str(sender.id)].tagged.append(tm)
            await self.save_balls()

        missed = random.randint(0, 100) >= sender_profile['accuracy']
        avoided = random.randint(0, 100) <= target_profile['avoidance']

        if missed:
            await ctx.send(f"⛄️ {sender.mention} threw a snowball on {target.mention}, but missed.")
        elif avoided:
            await ctx.send(f"🏂️ {sender.mention} threw a snowball on {target.mention}, but {target.mention} ducked and avoided the ball.")
        else:
            if not str(sender.id) in target_profile['snow_killed_by']:
                target_profile['snow_killed_by'].append(str(sender.id))
                if len(target_profile['snow_killed_by']) >= target_profile['lives'] and target_profile.get("team", None) is None:
                    target_profile['team'] = "snow"
            await ctx.send(f"☃️ {sender.mention} threw a snowball at {target.mention}.")
        await self.save_profiles()

    @commands.command(hidden=True)
    async def fireball(self, ctx, target: discord.Member):
        """
        Throw fireballs at people.
        """

        # if ctx.channel.id != 593075880717189123:
        #     await ctx.send("🔥 Wrong channel. Please use #sniping-grounds", delete_after=10)
        #     return

        sender = ctx.author
        role = ctx.guild.get_role(593010706400411671)

        sender_profile = await self.get_profile(member_id=int(sender.id))
        target_profile = await self.get_profile(member_id=int(target.id))

        sender_team = sender_profile.get("team", None)

        if sender_team == "snow":
            await ctx.send("❄️ You don't have any more fire. Use snow instead.")
            return

        if role not in sender.roles:
            await ctx.send("🔥️ You don't have any fire (yet)")
            return

        if sender_profile['cooldown_time_nextok'] > int(time.time()):
            await ctx.send("🤷️ Wait a little, you have no more balls...")
            return
        else:
            sender_profile['cooldown_time_nextok'] = int(time.time()) + sender_profile['cooldown_time']

        if not role in target.roles:
            await target.add_roles(role, reason=f"Fireballed by {sender.name}#{sender.discriminator}")
            await ctx.guild.get_channel(593011582510956544).send(f"{sender.mention} 🔥 {target.mention}")

            tm = TreeMember(str(target.id))

            self.trees["fireballs"]["population"][str(target.id)] = tm
            self.trees["fireballs"]["population"][str(sender.id)].tagged.append(tm)
            await self.save_balls()

        missed = random.randint(0, 100) >= sender_profile['accuracy']
        avoided = random.randint(0, 100) <= target_profile['avoidance']

        if missed:
            await ctx.send(f"👨‍🚒️ {sender.mention} threw a fireball on {target.mention}, but missed.")
        elif avoided:
            await ctx.send(f"👨‍🚒️ {sender.mention} threw a fireball on {target.mention}, but {target.mention} ducked and avoided the ball.")
        else:
            if not str(sender.id) in target_profile['fire_killed_by']:
                target_profile['fire_killed_by'].append(str(sender.id))
                if len(target_profile['fire_killed_by']) >= target_profile['lives'] and target_profile.get("team", None) is None:
                    target_profile['team'] = "fire"
            await ctx.send(f"🎆️ {sender.mention} threw a fireball at {target.mention}.")
        await self.save_profiles()


setup = Balls.setup
