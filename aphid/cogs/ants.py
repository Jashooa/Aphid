import logging

import discord
from bs4 import BeautifulSoup
from discord.ext import commands

log = logging.getLogger(__name__)


class Ants:
    """Ant-related commands."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(description='Bring up some simple info on an ant genus or species.')
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5.0)
    async def ant(self, ctx, genus: str, species: str=None, subspecies: str=None):
        """Bring up some simple info on an ant genus or species."""

        genus = genus.lower().capitalize()

        if species is not None:
            species = species.lower()

        if subspecies is not None:
            subspecies = subspecies.lower()

        if species is None:
            antwiki_url = f'http://antwiki.org/wiki/{genus}'
            antweb_url = f'http://antweb.org/description.do?genus={genus}&rank=genus'
        elif subspecies is None:
            antwiki_url = f'http://antwiki.org/wiki/{genus}_{species}'
            antweb_url = f'http://antweb.org/description.do?genus={genus}&species={species}&rank=species'
        else:
            antwiki_url = f'http://antwiki.org/wiki/{genus}_{species}_{subspecies}'
            antweb_url = f'http://antweb.org/description.do?genus={genus}&species={species}&subspecies={subspecies}&rank=subspecies'

        async with ctx.channel.typing():
            async with self.bot.session.get(antwiki_url) as resp:
                text = await resp.read()
                antwiki_soup = BeautifulSoup(text, 'html.parser')

            error = antwiki_soup.find('table', attrs={'class': 'infobox biota'})

            if error is not None:
                name = antwiki_soup.find('h1', id='firstHeading').span.i.text

                image = antwiki_soup.find('table', attrs={'class': 'infobox biota'}).find('img')
                image = image['src'] if image is not None else None
                image = f'http://antwiki.org{image}' if image is not None else ''

                subfamily = antwiki_soup.find('span', attrs={'class': 'subfamily'})
                subfamily = subfamily.a.text if subfamily is not None else ''

                tribe = antwiki_soup.find('span', attrs={'class': 'tribe'})
                tribe = tribe.a.text if tribe is not None else ''

                embed = discord.Embed(colour=discord.Colour.green())
                embed.title = name
                embed.set_thumbnail(url=image)
                embed.description = f'**Subfamily:** {subfamily}\n**Tribe:** {tribe}'
                embed.add_field(name='AntWiki', value=antwiki_url)
                embed.add_field(name='AntWeb', value=antweb_url)

                await ctx.send(embed=embed)
            else:
                await ctx.send('Not found.')


def setup(bot):
    bot.add_cog(Ants(bot))
