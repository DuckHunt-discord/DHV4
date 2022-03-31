import asyncio
import datetime
import random
import time
from typing import Optional

import discord
import typing

from babel.dates import format_timedelta
from discord.utils import escape_markdown

from utils import config
from utils.bot_class import MyBot
from utils.bushes import bushes_objects, bushes_weights
from utils.coats import Coats
from utils.events import Events
from utils.interaction import get_webhook_if_possible, anti_bot_zero_width
from utils.models import DiscordChannel, get_from_db, Player, get_player, SunState
from utils.translations import translate, ntranslate
import utils.ducks_config as ducks_config

SECOND = 1
MINUTE = 60 * SECOND
HOUR = 60 * MINUTE
DAY = 24 * HOUR


def _(s):
    return s


class Duck:
    """
    The standard duck. Kill it with the pan command
    """
    category = _('normal')
    fake = False  # Fake ducks only exists when they are alone on a channel. They are used for taunt messages, mostly.
    use_bonus_exp = True
    leave_on_hug = False

    def __init__(self, bot: MyBot, channel: discord.TextChannel):
        self.bot = bot
        self.channel = channel
        self._db_channel: Optional[DiscordChannel] = None

        self._webhook_parameters = {'avatar_url': random.choice(self.get_cosmetics()['avatar_urls']),
                                    'username': random.choice(self.get_cosmetics()['usernames'])}

        self.spawned_at: Optional[int] = None
        self.target_lock = asyncio.Lock()
        self.target_lock_by: Optional[discord.Member] = None
        self.db_target_lock_by: Optional[Player] = None

        self._lives: Optional[int] = None
        self.lives_left: Optional[int] = self._lives
        self._translate_function = None
        self._ntranslate_function = None

    def serialize(self):
        return {'category': self.category,
                'spawned_at': self.spawned_at,
                'spawned_for': self.spawned_for,
                'lives_left': self.lives_left,
                'lives': self._lives,
                'webhook_parameters': self._webhook_parameters}

    @classmethod
    def deserialize(cls, bot: MyBot, channel: discord.TextChannel, data: dict):
        d = cls(bot, channel)
        d.spawned_at = time.time() - data['spawned_for']
        d.lives_left = data['lives_left']
        d._lives = data['lives']
        d._webhook_parameters = data['webhook_parameters']

        return d

    def get_cosmetics(self):
        return getattr(ducks_config, self.category)

    @property
    def spawned_for(self):
        if self.spawned_at:
            return max(time.time() - self.spawned_at, 0)
        return None

    async def is_killed(self):
        await self.get_lives()
        return self.lives_left <= 0

    # Database #

    async def get_translate_function(self):
        if not self._translate_function:
            db_guild = await get_from_db(self.channel.guild)
            language = db_guild.language

            def _(message, **kwargs):
                return translate(message, language).format(**kwargs)

            self._translate_function = _

        return self._translate_function

    async def get_ntranslate_function(self):
        if not self._ntranslate_function:
            db_guild = await get_from_db(self.channel.guild)
            language = db_guild.language

            def ngettext(singular, plurial, n, **kwargs):
                return ntranslate(singular, plurial, n, language).format(**kwargs)

            self._ntranslate_function = ngettext

        return self._ntranslate_function

    async def get_db_channel(self):
        if not self._db_channel:
            self._db_channel = await get_from_db(self.channel)

        return self._db_channel

    async def get_webhook_parameters(self) -> dict:
        _ = await self.get_translate_function()
        webhook = self._webhook_parameters
        webhook['username'] = _(webhook['username'])
        return webhook

    async def get_exp_value(self) -> int:
        db_channel = await self.get_db_channel()
        lives = await self.get_lives()
        exp = db_channel.base_duck_exp + db_channel.per_life_exp * (lives - 1)

        if self.bot.current_event == Events.UN_TREATY:
            exp += int(db_channel.per_life_exp / 2 * (lives - 1))

        return exp

    async def get_accuracy(self, base_accuracy) -> int:
        #  db_hunter = self.db_target_lock_by

        return base_accuracy

    async def increment_hurts(self):
        db_hurter = self.db_target_lock_by
        db_hurter.hurted[self.category] += 1

    async def increment_kills(self):
        db_killer = self.db_target_lock_by
        db_killer.killed[self.category] += 1

    async def increment_hugs(self):
        db_hugger = self.db_target_lock_by
        db_hugger.hugged[self.category] += 1

    async def increment_resists(self):
        db_hurter = self.db_target_lock_by
        db_hurter.resisted[self.category] += 1

    async def increment_frightens(self):
        db_frightener = self.db_target_lock_by
        db_frightener.frightened[self.category] += 1

    async def set_best_time(self):
        db_hunter = self.db_target_lock_by
        db_hunter.best_times[self.category] = min(self.spawned_for, db_hunter.best_times[self.category])

    # Locks #

    async def target(self, member: discord.Member = None):
        await self.target_lock.acquire()
        if member:
            self.target_lock_by = member
            self.db_target_lock_by = await get_player(member, self.channel)

        await self.get_db_channel()

    async def release(self):
        self.target_lock_by = None
        self.db_target_lock_by = None
        self.target_lock.release()

    # Messages #

    async def get_trace(self) -> str:
        traces = self.get_cosmetics()['traces']
        trace = escape_markdown(random.choice(traces))

        return anti_bot_zero_width(trace)

    async def get_face(self) -> str:
        db_channel = await self.get_db_channel()

        dtnow = datetime.datetime.now()
        if dtnow.day == 1 and dtnow.month == 4 and self.category == "normal":
            if not db_channel.use_emojis:
                faces = ["><(((º>", "< )))) ><", ">--) ) ) )*>", "><((((>", "><(((('>", "くコ:彡"]
                face = escape_markdown(random.choice(faces))
            else:
                faces = ["🐟", "🐠", "🐡"]
                face = random.choice(faces)
        else:
            if not db_channel.use_emojis:
                faces = self.get_cosmetics()['faces']
                face = escape_markdown(random.choice(faces))
            else:
                faces = self.get_cosmetics()['emojis']
                face = random.choice(faces)

        return face

    async def get_shout(self) -> str:
        _ = await self.get_translate_function()
        shouts = self.get_cosmetics()['shouts']

        shout = _(random.choice(shouts))
        if "http" in shout:
            return shout
        else:
            return anti_bot_zero_width(shout)

    async def get_bye_trace(self) -> str:
        _ = await self.get_translate_function()
        traces = self.get_cosmetics()['bye_traces']

        trace = _(random.choice(traces))

        return anti_bot_zero_width(discord.utils.escape_markdown(trace))

    async def get_bye_shout(self) -> str:
        _ = await self.get_translate_function()
        shouts = self.get_cosmetics()['bye_shouts']

        shout = _(random.choice(shouts))

        return anti_bot_zero_width(shout)

    async def get_spawn_message(self) -> str:
        trace = await self.get_trace()
        face = await self.get_face()
        shout = await self.get_shout()

        return f"{trace} {face} {shout}"

    async def get_ncategory_killed(self, this_ducks_killed):
        ngettext = await self.get_ntranslate_function()
        return ngettext("of which one is a normal duck",
                        "of which {this_ducks_killed} are normal ducks",
                        this_ducks_killed,
                        this_ducks_killed=this_ducks_killed,
                        )

    async def get_kill_message(self, killer, db_killer: Player, won_experience: int, bonus_experience: int) -> str:
        _ = await self.get_translate_function()
        ngettext = await self.get_ntranslate_function()
        db_guild = await get_from_db(self.channel.guild)

        locale = db_guild.language

        spawned_for = datetime.timedelta(seconds=self.spawned_for)
        if locale.startswith("ru"):
            spawned_for_str = format_timedelta(spawned_for, locale=locale, format="short")
        else:
            spawned_for_str = format_timedelta(spawned_for, locale=locale, threshold=1.20)

        total_ducks_killed = sum(db_killer.killed.values())
        this_ducks_killed = db_killer.killed.get(self.category)

        if bonus_experience:
            normal_exp = won_experience - bonus_experience

            return _(
                "{killer.mention} killed the duck in {spawned_for_str}, "
                "for a total of {total_ducks_killed} "
                "({ncategory_killed}) "
                "[**Killed**: {normal_exp} exp + {bonus_experience} **clover**]",
                killer=killer,
                normal_exp=normal_exp,
                bonus_experience=bonus_experience,
                spawned_for_str=spawned_for_str,
                total_ducks_killed=total_ducks_killed,
                ncategory_killed=await self.get_ncategory_killed(this_ducks_killed),
            )
        else:
            return _(
                "{killer.mention} killed the duck in {spawned_for_str}, "
                "for a total of {total_ducks_killed} "
                "({ncategory_killed}) "
                "[**Killed**: {normal_exp} exp]",
                killer=killer,
                normal_exp=won_experience,
                spawned_for_str=spawned_for_str,
                total_ducks_killed=total_ducks_killed,
                ncategory_killed=await self.get_ncategory_killed(this_ducks_killed),
            )

    async def get_frighten_message(self, hunter, db_hunter: Player) -> str:
        _ = await self.get_translate_function()

        return _("{hunter.mention} scared the duck away.",
                 hunter=hunter, )

    async def get_hurt_message(self, hurter, db_hurter, damage) -> str:
        _ = await self.get_translate_function()
        db_channel = await self.get_db_channel()

        if db_channel.show_duck_lives:
            total_lives = await self.get_lives()
            lives_left = self.lives_left
            return _(
                "{hurter.mention} hurt the duck [**SUPER DUCK detected**: {lives_left}/{total_lives}][**Damage** : -{damage}]",
                hurter=hurter,
                damage=damage,
                lives_left=lives_left,
                total_lives=total_lives,
            )
        else:
            return _("{hurter.mention} hurt the duck [**SUPER DUCK detected**][**Damage** : -{damage}]",
                     hurter=hurter,
                     damage=damage)

    async def get_resists_message(self, hurter, db_hurter) -> str:
        _ = await self.get_translate_function()

        return _("{hurter.mention}, the duck RESISTED. [**ARMORED DUCK detected**]",
                 hurter=hurter, )

    async def get_hug_message(self, hugger, db_hugger, experience) -> str:
        _ = await self.get_translate_function()
        if experience > 0:
            return _("{hugger.mention} hugged the duck. So cute! [**Hug**: +{experience} exp]",
                     hugger=hugger,
                     experience=experience,
                     )
        else:
            if hugger.id == 296573428293697536:  # ⚜WistfulWizzz⚜#5928
                return _("<:Wizzz:505828171397070848> Wizzz huggy ducky! So cute!")
            return _(
                "{hugger.mention} tried to hug the duck. So cute! Unfortunately, the duck hates you, because you killed all his family. [**FAIL**: {experience} exp]",
                hugger=hugger,
                experience=experience,
            )

    async def get_left_message(self) -> str:
        trace = await self.get_bye_trace()
        shout = await self.get_bye_shout()

        return f"{shout} {trace}"

    async def send(self, content: str, **kwargs):
        db_channel = await self.get_db_channel()
        if db_channel.use_webhooks:
            webhook = await get_webhook_if_possible(self.bot, db_channel)
        else:
            webhook = None

        if webhook:
            this_webhook_parameters = await self.get_webhook_parameters()

            async def sendit():
                try:
                    await webhook.send(content, **this_webhook_parameters, **kwargs)
                    return
                except (discord.NotFound, ValueError) as e:
                    db_channel: DiscordChannel = await get_from_db(self.channel)
                    self.bot.logger.warning(f"Removing webhook {webhook.url} on #{self.channel.name} on {self.channel.guild.id} from planification because {e}.")
                    db_channel.webhook_urls.remove(webhook.url)
                    await db_channel.save()
                    try:
                        await self.channel.send(content, **kwargs)
                    except (discord.Forbidden, discord.NotFound):
                        self.bot.logger.warning(
                            f"Removing #{self.channel.name} on {self.channel.guild.id} from planification because I'm not allowed to send messages there {e}.")
                        try:
                            del self.bot.enabled_channels[self.channel]
                        except KeyError:
                            pass
                        try:
                            del self.bot.ducks_spawned[self.channel]
                        except KeyError:
                            pass

            asyncio.ensure_future(sendit())
            return

        async def sendit():
            try:
                await self.channel.send(content, **kwargs)
            except (discord.Forbidden, discord.NotFound):
                self.bot.logger.warning(
                    f"Removing #{self.channel.name} on {self.channel.guild.id} from planification because I'm not allowed to send messages there.")
                try:
                    del self.bot.enabled_channels[self.channel]
                except KeyError:
                    pass
                try:
                    del self.bot.ducks_spawned[self.channel]
                except KeyError:
                    pass

        asyncio.ensure_future(sendit())

    # Parameters #

    async def get_time_left(self) -> float:
        db_channel = await self.get_db_channel()

        should_disappear_after = db_channel.ducks_time_to_live
        return should_disappear_after - self.spawned_for

    async def initial_set_lives(self):
        self._lives = 1

    async def get_lives(self):
        if not self._lives:
            await self.initial_set_lives()
            self.lives_left = self._lives
        return self._lives

    async def get_damage(self):
        if self.bot.current_event == Events.UN_TREATY:
            return 1
        db_hugger = self.db_target_lock_by
        if db_hugger.is_powerup_active('explosive_ammo'):
            return 3
        elif db_hugger.is_powerup_active('ap_ammo'):
            return 2
        else:
            return 1

    async def get_hug_experience(self):
        return -2

    async def will_frighten(self):
        db_channel = await self.get_db_channel()
        db_hunter = self.db_target_lock_by

        if not db_hunter.is_powerup_active('silencer'):
            frighten_chance = db_channel.duck_frighten_chance
            coat_color = db_hunter.get_current_coat_color()
            if coat_color == Coats.ORANGE:
                frighten_chance += 3
            elif coat_color == Coats.CAMO:
                frighten_chance -= 3
            return random.randint(1, 100) <= frighten_chance
        else:
            return False

    # Entry Points #

    async def spawn(self, loud=True):
        total_lives = await self.get_lives()

        bot = self.bot
        message = await self.get_spawn_message()

        if loud:
            self.bot.logger.debug(f"Spawning {self}", guild=self.channel.guild, channel=self.channel)
            self.spawned_at = time.time()
            await self.send(message)

        bot.ducks_spawned[self.channel].append(self)

    async def shoot(self, args) -> Optional[bool]:
        if await self.will_frighten():
            return await self.frighten()

        damage = await self.get_damage()

        if await self.damage(damage):
            await self.kill(damage, args)
        else:
            await self.hurt(damage, args)
        return None

    async def hug(self, args):
        if self.leave_on_hug:
            self.despawn()
            await self.set_best_time()

        hugger = self.target_lock_by
        db_hugger = self.db_target_lock_by

        experience = await self.get_hug_experience()
        await self.increment_hugs()
        await self.release()

        await db_hugger.edit_experience_with_levelups(ctx=self.channel, delta=experience, bot=self.bot)

        await db_hugger.save()

        _ = await self.get_translate_function()
        await self.send(await self.get_hug_message(hugger, db_hugger, experience))

    async def leave(self):
        self.bot.logger.debug(f"Leaving {self}", guild=self.channel.guild, channel=self.channel)

        await self.send(await self.get_left_message())
        self.despawn()

    async def maybe_leave(self):
        db_channel = await self.get_db_channel()
        if db_channel.ducks_time_to_live < self.spawned_for:
            await self.leave()
            return True
        else:
            return False

    async def maybe_bushes_message(self, hunter, db_hunter) -> typing.Optional[typing.Callable]:
        bush_chance = 13
        coat_color = db_hunter.get_current_coat_color()

        if coat_color == Coats.BLUE:
            bush_chance += 7

        if not random.randint(1, 100) <= bush_chance:
            return None

        db_channel = await self.get_db_channel()

        item_found = random.choices(bushes_objects, bushes_weights)[0]()

        gave_item = await item_found.give(db_channel, db_hunter)

        if gave_item:
            db_hunter.found_items['took_' + item_found.db] += 1
        else:
            db_hunter.found_items['left_' + item_found.db] += 1

        _ = await self.get_translate_function()
        args = await item_found.send_args(_, gave_item)

        args['content'] = f"{hunter.mention} > " + args.get('content', '')

        async def send_result():
            await self.send(**args)

        return send_result

    # Actions #
    async def frighten(self):
        hunter = self.target_lock_by
        db_hunter = self.db_target_lock_by
        await self.increment_frightens()
        self.despawn()
        await self.release()

        await db_hunter.save()
        await self.send(await self.get_frighten_message(hunter, db_hunter))

    async def kill(self, damage: int, args):
        """The duck was killed by the current target player"""
        self.despawn()
        await self.set_best_time()

        killer = self.target_lock_by
        db_killer = self.db_target_lock_by
        await self.increment_kills()
        await self.release()

        _ = await self.get_translate_function()

        # Increment killed by 1
        won_experience = await self.get_exp_value()

        bonus_experience = 0
        if self.use_bonus_exp:
            bonus_experience = await db_killer.get_bonus_experience(won_experience)
            db_killer.shooting_stats['bonus_experience_earned'] += bonus_experience
            won_experience += bonus_experience

        await db_killer.edit_experience_with_levelups(self.channel, won_experience, bot=self.bot)

        bushes_coro = await self.maybe_bushes_message(killer, db_killer)

        await self.send(await self.get_kill_message(killer, db_killer, won_experience, bonus_experience))
        if bushes_coro is not None:
            await bushes_coro()

        await self.post_kill(killer, db_killer, won_experience, bonus_experience)

    async def hurt(self, damage: int, args):
        hurter = self.target_lock_by
        db_hurter = self.db_target_lock_by

        if damage:
            await self.increment_hurts()
            await self.send(await self.get_hurt_message(hurter, db_hurter, damage))
        else:
            await self.increment_resists()
            await self.send(await self.get_resists_message(hurter, db_hurter))

        await self.release()
        await db_hurter.save()

    # Utilities #

    def despawn(self):
        try:
            self.bot.ducks_spawned[self.channel].remove(self)
        except ValueError:
            pass

    async def damage(self, lives):
        """
        This function remove lives from a duck and returns True if the duck was killed, False otherwise
        """
        self.lives_left = self.lives_left - lives
        return await self.is_killed()

    async def post_kill(self, killer, db_killer, won_experience, bonus_experience):
        """
        Just in case you want to do something after a duck died.
        """
        await db_killer.save()

    def __repr__(self):
        attributes = []
        ll = self.lives_left  # No await
        if ll is not None and ll <= 0:
            attributes.append("killed")
        if self in self.bot.ducks_spawned[self.channel]:
            attributes.append(f"spawned-{self.spawned_for}s")

        total_lives = self._lives  # We can't await here, so try our best

        return f"<{type(self).__name__} {self.category} {' '.join(attributes)} lives={self.lives_left}/{total_lives}>"


# Standard ducks #


class GhostDuck(Duck):
    """
    A rare duck that does *not* say anything when it spawns.
    """
    category = _('ghost')
    fake = False  # Fake ducks only exists when they are alone on a channel. They are used for taunt messages, mostly.

    async def get_ncategory_killed(self, this_ducks_killed):
        ngettext = await self.get_ntranslate_function()
        return ngettext("of which one is a ghost duck",
                        "of which {this_ducks_killed} are ghost ducks",
                        this_ducks_killed,
                        this_ducks_killed=this_ducks_killed,
                        )

    async def spawn(self, loud=True):
        total_lives = await self.get_lives()

        bot = self.bot

        bot.ducks_spawned[self.channel].append(self)

        self.spawned_at = time.time()


class PrDuck(Duck):
    """
    Duck that will ask a simple math question to be killed
    """
    category = _('prof')

    def __init__(self, bot: MyBot, channel: discord.TextChannel):
        super().__init__(bot, channel)
        r1 = random.randint(0, 100)
        r2 = random.randint(0, 100)
        self.operation = f"{r1} + {r2}"
        self.answer = r1 + r2

    def serialize(self):
        return {**super().serialize(), 'operation': self.operation, 'answer': self.answer}

    @classmethod
    def deserialize(cls, bot: MyBot, channel: discord.TextChannel, data: dict):
        d = super().deserialize(bot, channel, data)
        d.operation = data['operation']
        d.answer = data['answer']
        return d

    async def get_ncategory_killed(self, this_ducks_killed):
        ngettext = await self.get_ntranslate_function()
        return ngettext("of which one is a professor duck",
                        "of which {this_ducks_killed} are Pr. ducks",
                        this_ducks_killed,
                        this_ducks_killed=this_ducks_killed,
                        )

    async def get_shout(self) -> str:
        _ = await self.get_translate_function()

        return _("Huh, quick question, what's {operation} ?", operation=self.operation)

    async def shoot(self, args: list):
        _ = await self.get_translate_function()
        hurter = self.target_lock_by

        try:
            result = int(args[0])
        except IndexError:
            await self.send(
                _("{hurter.mention}, I asked you a question ! What's {operation} ? Answer with `dh!bang <answer>`.",
                  hurter=hurter,
                  operation=self.operation))
            await self.release()
            return False
        except ValueError:
            await self.send(_("{hurter.mention}, Just give me digits !",
                              hurter=hurter))
            await self.release()
            return False

        if result != self.answer:
            await self.send(_("{hurter.mention}, that's not the correct answer !",
                              hurter=hurter))
            await self.release()
            return False
        else:
            await super().shoot(args)
            return True

    async def get_exp_value(self):
        return round(await super().get_exp_value() * 1.2)


class BabyDuck(Duck):
    """
    A baby duck. You shouldn't kill a baby duck. If you do, your exp will suffer.
    """
    category = _('baby')
    leave_on_hug = True
    use_bonus_exp = False

    async def get_ncategory_killed(self, this_ducks_killed):
        ngettext = await self.get_ntranslate_function()
        return ngettext("of which one is a baby duck",
                        "of which {this_ducks_killed} are baby ducks",
                        this_ducks_killed,
                        this_ducks_killed=this_ducks_killed,
                        )

    async def get_kill_message(self, killer, db_killer: Player, won_experience: int, bonus_experience: int):
        _ = await self.get_translate_function()
        return _("{killer.mention} killed the Baby Duck [**Baby**: {won_experience} exp]", killer=killer,
                 won_experience=won_experience, bonus_experience=bonus_experience)

    async def get_exp_value(self):
        return - await super().get_exp_value()

    async def get_hug_experience(self):
        return 5

    async def get_hug_message(self, hugger, db_hugger, experience) -> str:
        spawned_for = datetime.timedelta(seconds=self.spawned_for)

        db_guild = await get_from_db(self.channel.guild)

        locale = db_guild.language

        if locale.startswith("ru"):
            spawned_for_str = format_timedelta(spawned_for, locale=locale, format="short")
        else:
            spawned_for_str = format_timedelta(spawned_for, locale=locale, threshold=1.20)

        _ = await self.get_translate_function()
        return _("{hugger.mention} hugged the duck in {spawned_for_str}. So cute! [**Hug**: +{experience} exp]",
                 hugger=hugger,
                 experience=experience,
                 spawned_for_str=spawned_for_str,
                 )


class GoldenDuck(Duck):
    """
    Duck worth twice the usual experience
    """
    category = _('golden')

    async def get_ncategory_killed(self, this_ducks_killed):
        ngettext = await self.get_ntranslate_function()
        return ngettext("of which one is a golden duck",
                        "of which {this_ducks_killed} are golden ducks",
                        this_ducks_killed,
                        this_ducks_killed=this_ducks_killed,
                        )

    async def get_exp_value(self):
        return await super().get_exp_value() * 2


class PlasticDuck(Duck):
    """
    Worthless duck (half the exp)
    """
    category = _('plastic')

    async def get_ncategory_killed(self, this_ducks_killed):
        ngettext = await self.get_ntranslate_function()
        return ngettext("of which one is made of plastic",
                        "of which {this_ducks_killed} are made of plastic",
                        this_ducks_killed,
                        this_ducks_killed=this_ducks_killed,
                        )

    async def will_frighten(self):
        return False

    async def get_exp_value(self):
        return round(await super().get_exp_value() * 0.5)


class KamikazeDuck(Duck):
    """
    This duck kills every other duck on the channel when leaving
    """
    category = _('kamikaze')

    async def get_ncategory_killed(self, this_ducks_killed):
        ngettext = await self.get_ntranslate_function()
        return ngettext("of which one is a kamikaze duck",
                        "of which {this_ducks_killed} are kamikaze ducks",
                        this_ducks_killed,
                        this_ducks_killed=this_ducks_killed,
                        )

    async def leave(self):
        await self.send(await self.get_left_message())
        self.bot.ducks_spawned[self.channel].clear()


class MechanicalDuck(Duck):
    """
    This duck is not really a duck...
    """
    category = _('mechanical')
    fake = True
    use_bonus_exp = False

    def __init__(self, *args, creator: Optional[discord.Member] = None, **kwargs):
        super().__init__(*args, **kwargs)

        self.creator = creator

    def serialize(self):
        return {**super().serialize(), 'creator': self.creator}

    @classmethod
    def deserialize(cls, bot: MyBot, channel: discord.TextChannel, data: dict):
        d = super().deserialize(bot, channel, data)
        d.creator = data['creator']
        return d

    async def get_exp_value(self):
        return -10

    async def get_ncategory_killed(self, this_ducks_killed):
        ngettext = await self.get_ntranslate_function()
        return ngettext("of which one is a mechanical duck",
                        "of which {this_ducks_killed} are mechanical ducks",
                        this_ducks_killed,
                        this_ducks_killed=this_ducks_killed,
                        )

    async def get_kill_message(self, killer, db_killer, won_experience, bonus_experience):
        _ = await self.get_translate_function()

        creator = self.creator
        if not creator:
            return _(
                "Damn, {killer.mention}, you suck! You killed a mechanical duck! I wonder who made it? [exp: {won_experience}]",
                killer=killer,
                won_experience=won_experience)
        else:
            return _(
                "Damn, {killer.mention}, you suck! You killed a mechanical duck! All of this is {creator.mention}'s fault! [exp: {won_experience}]",
                killer=killer,
                won_experience=won_experience,
                creator=creator)

    async def post_kill(self, killer, db_killer, won_experience, bonus_experience):
        if self.creator and killer.id == self.creator.id:
            db_killer.stored_achievements['short_memory'] = True

        await super().post_kill(killer, db_killer, won_experience, bonus_experience)


# Super ducks #

class SuperDuck(Duck):
    """
    A duck with many lives to spare.
    """
    category = _('super')

    def __init__(self, *args, lives: int = None, **kwargs):
        super().__init__(*args, **kwargs)

        self._lives = lives
        self.lives_left = lives

    async def get_ncategory_killed(self, this_ducks_killed):
        ngettext = await self.get_ntranslate_function()
        return ngettext("of which one is a super duck",
                        "of which {this_ducks_killed} are super ducks",
                        this_ducks_killed,
                        this_ducks_killed=this_ducks_killed,
                        )

    async def initial_set_lives(self):
        db_channel = await self.get_db_channel()
        max_life = db_channel.super_ducks_max_life
        if self.bot.current_event == Events.MEGA_DUCKS:
            max_life += 4

        min_lives, max_lives = db_channel.super_ducks_min_life, max_life

        self._lives = random.randint(min(min_lives, max_lives), max(min_lives, max_lives))


class MotherOfAllDucks(SuperDuck):
    """
    This duck will spawn two more when she dies.
    """
    category = _('moad')

    async def get_ncategory_killed(self, this_ducks_killed):
        ngettext = await self.get_ntranslate_function()
        return ngettext("of which one is a MOAD",
                        "of which {this_ducks_killed} are MOADs",
                        this_ducks_killed,
                        this_ducks_killed=this_ducks_killed,
                        )

    async def post_kill(self, killer, db_killer, won_experience, bonus_experience):
        for i in range(2):
            # Discord sucks
            # When you send two messages (one after the other but close enough),
            # they will be shown in the wrong order for *some*, but not all viewers of the channel.
            # To fix that we sleep a bit before spawning ducks
            await asyncio.sleep(.5)
            d = await spawn_random_weighted_duck(self.bot, self.channel)
            if d.category == "baby":
                db_killer.stored_achievements['you_monster'] = True

        await super().post_kill(killer, db_killer, won_experience, bonus_experience)


class ArmoredDuck(SuperDuck):
    """
    This duck will resist a damage of 1.
    """
    category = _('armored')

    async def get_ncategory_killed(self, this_ducks_killed):
        ngettext = await self.get_ntranslate_function()
        return ngettext("of which one is an armored duck",
                        "of which {this_ducks_killed} are armored ducks",
                        this_ducks_killed,
                        this_ducks_killed=this_ducks_killed,
                        )

    async def get_damage(self):
        if self.bot.current_event == Events.UN_TREATY:
            return 1
        minus = 0
        if random.randint(1, 100) < 90:
            minus = 1

        return await super().get_damage() - minus

    async def get_hurt_message(self, hurter, db_hurter, damage) -> str:
        _ = await self.get_translate_function()
        db_channel = await self.get_db_channel()

        if db_channel.show_duck_lives:
            total_lives = await self.get_lives()
            lives_left = self.lives_left

            return _(
                "{hurter.mention} hurt the duck [**ARMORED duck detected**: {lives_left}/{total_lives}][**Damage** : -{damage}]",
                hurter=hurter,
                damage=damage,
                lives_left=lives_left,
                total_lives=total_lives,
            )
        else:
            return _("{hurter.mention} hurt the duck [**ARMORED duck detected**][**Damage** : -{damage}]",
                     hurter=hurter,
                     damage=damage)


class NightDuck(Duck):
    """
    A normal duck that only spawns at night.
    """
    category = _('night')

    async def get_ncategory_killed(self, this_ducks_killed):
        ngettext = await self.get_ntranslate_function()
        return ngettext("of which one is a night duck",
                        "of which {this_ducks_killed} are night ducks",
                        this_ducks_killed,
                        this_ducks_killed=this_ducks_killed,
                        )


class SleepingDuck(Duck):
    """
    An un-miss-able duck that you can only shot at night
    """
    category = _('sleeping')

    async def get_ncategory_killed(self, this_ducks_killed):
        ngettext = await self.get_ntranslate_function()
        return ngettext("of which one is a sleeping duck",
                        "of which {this_ducks_killed} are sleeping ducks",
                        this_ducks_killed,
                        this_ducks_killed=this_ducks_killed,
                        )

    async def get_accuracy(self, base_accuracy) -> int:
        return 100


RANDOM_DAYTIME_SPAWN_DUCKS_CLASSES = [Duck, GhostDuck, PrDuck, BabyDuck, GoldenDuck, PlasticDuck, KamikazeDuck,
                                      MechanicalDuck, SuperDuck, MotherOfAllDucks, ArmoredDuck]
DUCKS_DAYTIME_CATEGORIES_TO_CLASSES = {dc.category: dc for dc in RANDOM_DAYTIME_SPAWN_DUCKS_CLASSES}
DUCKS_DAYTIME_CATEGORIES = [dc.category for dc in RANDOM_DAYTIME_SPAWN_DUCKS_CLASSES]

RANDOM_NIGHTTIME_SPAWN_DUCKS_CLASSES = [NightDuck, SleepingDuck]
DUCKS_NIGHTTIME_CATEGORIES_TO_CLASSES = {dc.category: dc for dc in RANDOM_NIGHTTIME_SPAWN_DUCKS_CLASSES}
DUCKS_NIGHTTIME_CATEGORIES = [dc.category for dc in RANDOM_NIGHTTIME_SPAWN_DUCKS_CLASSES]

RANDOM_SPAWN_DUCKS_CLASSES = RANDOM_DAYTIME_SPAWN_DUCKS_CLASSES + RANDOM_NIGHTTIME_SPAWN_DUCKS_CLASSES
DUCKS_CATEGORIES_TO_CLASSES = {dc.category: dc for dc in RANDOM_SPAWN_DUCKS_CLASSES}
DUCKS_CATEGORIES = [dc.category for dc in RANDOM_SPAWN_DUCKS_CLASSES]


async def spawn_random_weighted_duck(bot: MyBot, channel: discord.TextChannel, db_channel: DiscordChannel = None, sun: SunState=None):
    duck = await get_random_weighted_duck(bot, channel, db_channel, sun)
    await duck.spawn()
    return duck


async def get_random_weighted_duck(bot: MyBot, channel: discord.TextChannel, db_channel: DiscordChannel = None, sun: SunState=None):
    if sun is None:
        sun, duration_of_night, time_left_sun = await compute_sun_state(channel)

    db_channel = db_channel or await get_from_db(channel)

    if sun == SunState.DAY:
        weights = [getattr(db_channel, f"spawn_weight_{category}_ducks") for category in DUCKS_DAYTIME_CATEGORIES]
        ducks = RANDOM_DAYTIME_SPAWN_DUCKS_CLASSES
    else:
        weights = [getattr(db_channel, f"spawn_weight_{category}_ducks") for category in DUCKS_NIGHTTIME_CATEGORIES]
        ducks = RANDOM_NIGHTTIME_SPAWN_DUCKS_CLASSES

    if bot.current_event == Events.STEROIDS and SuperDuck in ducks:
        weights[ducks.index(SuperDuck)] *= 2

    if sum(weights) <= 0:  # Channel config is fucked anyways
        return Duck(bot, channel)

    DuckClass: typing.Type[Duck] = random.choices(ducks, weights)[0]

    return DuckClass(bot, channel)


def deserialize_duck(bot: MyBot, channel: discord.TextChannel, data: dict):
    return DUCKS_CATEGORIES_TO_CLASSES[data['category']].deserialize(bot, channel, data)


async def compute_sun_state(channel, seconds_spent_today=None):
    if seconds_spent_today is None:
        now = int(time.time())
        first_second = now - now % DAY
        seconds_spent_today = now - first_second

    db_channel = await get_from_db(channel)
    night_start_at = db_channel.night_start_at
    night_end_at = db_channel.night_end_at

    if night_start_at == night_end_at:
        # Fastpath: No night defined
        sun = SunState.DAY
        duration_of_night = 0
        time_left_sun = DAY
    elif night_start_at <= seconds_spent_today <= night_end_at:
        # Case where night is from small to big
        # Ex : 0          <= 30                  <= 60
        sun = SunState.NIGHT
        duration_of_night = night_end_at - night_start_at
        time_left_sun = night_end_at - seconds_spent_today
    elif night_end_at <= night_start_at <= seconds_spent_today:
        # Case where the nights rolls over the next day
        # Ex : 25         <= 30                  <= 2
        sun = SunState.NIGHT
        duration_of_night = DAY - night_start_at + night_end_at
        time_left_sun = DAY - seconds_spent_today + night_end_at
    elif night_start_at >= night_end_at >= seconds_spent_today:
        # Case where the night rolls over the previous day
        # Ex : 25         <= 1                   <= 2
        sun = SunState.NIGHT
        duration_of_night = DAY - night_start_at + night_end_at
        time_left_sun = night_end_at - seconds_spent_today
    else:
        sun = SunState.DAY
        if night_start_at <= night_end_at:
            duration_of_night = night_end_at - night_start_at
            if seconds_spent_today <= night_start_at:
                time_left_sun = night_start_at - seconds_spent_today
            else:
                time_left_sun = DAY - seconds_spent_today + night_start_at

        else:  # night_end_at <= night_start_at:
            duration_of_night = DAY - night_start_at + night_end_at

            time_left_sun = night_start_at - seconds_spent_today

    return sun, duration_of_night, time_left_sun


del _
