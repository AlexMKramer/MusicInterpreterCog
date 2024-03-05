import discord
from discord import option
from discord.ext import commands
import os
from openai import OpenAI
from lyricsgenius import Genius
import re

import core.auto1111
import core.queueHandler
import core.utils as utils

genius = Genius(os.getenv('GENIUS_TOKEN'))


def gpt_integration(text):
    gpt_new_prompt = ({"role": "user", "content": "" + text})
    gpt_message = gpt_initial_prompt + [gpt_new_prompt]
    try:
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=gpt_message
        )
        reply_content = completion.choices[0].message.content
        start_index = reply_content.find('{')
        end_index = reply_content.rfind('}')

        if start_index != -1 and end_index != -1 and end_index > start_index:
            new_text = reply_content[start_index:end_index + 1]
            print(f'ChatGPT reply: {new_text}')
            return new_text
        else:
            print(f'ChatGPT reply: {reply_content}')
            return reply_content
    except Exception as e:
        print(e)
        return None


gpt_initial_prompt = [{'role': 'user',
                       'content': "Using song lyrics, come up with a prompt for an image generator.  "
                                  "Please follow the format exactly. The format should be broken down "
                                  "like this: {Art Style}, {Subject}, {Details}, {Color}\n The art style "
                                  "should be determined by the overall impression of the song.  If it is "
                                  "sad, then something like La Douleur should be used. If it is happy, "
                                  "perhaps a vibrant street art style.\nThe Subject should be determined "
                                  "by who the song is about.  If the song is about a couple trying to "
                                  "escape the city, then the subject should be a couple.\nThe Details "
                                  "should be determined by descriptive words used in the song.  If they "
                                  "mention empty bottles, then add empty bottles to the prompt.\nThe "
                                  "color should be determined by the mood of the song.  If the mood is a "
                                  "happy one, use bright colors.\nHere is an example:\n{A dreamlike and "
                                  "ethereal art style}, {a couple standing on a cliffside embracing, "
                                  "overlooking a surreal and beautiful landscape}, {sunset, grassy, "
                                  "soft wind}, {soft pastels, with hints of warm oranges and pinks}"},
                      {'role': 'assistant',
                       'content': "{Vibrant and energetic street art style}, {a group of friends dancing and "
                                  "celebrating under the city lights}, {joyful, urban, rhythm}, {bold and lively "
                                  "colors, with splashes of neon blues and pinks}"}, ]


# Clean up the lyrics removing unwanted text and advertisements
def fix_lyrics(text):
    keyword1 = "Lyrics"
    keyword2 = r"\d*Embed|Embed"
    start_index = text.find(keyword1)
    end_index = re.search(keyword2, text[start_index])
    try:
        if start_index != -1 and end_index:
            lyrics_in_index = start_index + end_index.start()
            text = text[start_index + len(keyword1):lyrics_in_index].strip()
        else:
            text = text
        ad_pattern = r'See .*? LiveGet tickets as low as \$\d+You might also like'
        re.sub(ad_pattern, '', text)
        re.sub(r'\[.*?\]', '', text)
        re.sub(r'\d+$', '', text)
        re.sub('"', '', text)
    except Exception as e:
        print(f'Error: {e}\'\nLyrics: {text}')
    return text


# Get the lyrics from Lyrics Genius API using the song and artist name
def get_lyrics(song, artist):
    try:
        song = genius.search_song(song, artist)
        new_lyrics = song.lyrics
        fixed_lyrics = fix_lyrics(new_lyrics)
        return fixed_lyrics
    except Exception as e:
        print(e)
        return None


# Setup checkpoint autocomplete
async def checkpoints_autocomplete(ctx: discord.AutocompleteContext):
    checkpoints = utils.get_checkpoints()
    return [checkpoint for checkpoint in checkpoints if checkpoint.startswith(ctx.value.lower())]


async def height_width_autocomplete(ctx: discord.AutocompleteContext):
    return [f"{hw['height']} {hw['width']}" for hw in utils.height_width_option]


# set up the main commands used by the bot
class MusicInterpreterCog(commands.Cog, name="MusicInterpreterCog", description="Generate images from song lyrics"):
    ctx_parse = discord.ApplicationContext

    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(description='Create images from text!', guild_only=True)
    @option(
        'song',
        str,
        description='The song name to generate images from.',
        required=True
    )
    @option(
        'artist',
        str,
        description='The artist name to generate images from.',
        required=True
    )
    @option(
        'model_name',
        str,
        description='Choose the checkpoint to use for generating the images with.',
        required=False,
        autocomplete=checkpoints_autocomplete
    )
    @option(
        'num_images',
        int,
        min_value=1,
        max_value=4,
        description='The number of images to generate up to 4.',
        required=False
    )
    @option(
        'height_width',
        str,
        description='The height of the images to generate.',
        required=False,
        autocomplete=height_width_autocomplete
    )
    @option(
        'steps',
        int,
        description='The number of steps to take in the diffusion process.',
        required=False
    )
    async def interpret(self, ctx: discord.ApplicationContext,
                        *,
                        song: str,
                        artist: str,
                        model_name,
                        num_images=4,
                        height_width="1152 896",
                        steps=25
                        ):
        if model_name is None:
            # Get a list of the checkpoints
            model_name = utils.get_checkpoints()
            # Check if there are any checkpoints available
            if not model_name:
                # send a message to the user that there are no checkpoints and break the command
                await ctx.respond("There are no checkpoints available to use for generating images. Try downloading a "
                                  "model and placing it in the checkpoints folder.")
                return
            else:
                model_name = model_name[0]
        model_path = os.path.join(os.getcwd(), "models/checkpoints/" + model_name + ".safetensors")
        print(model_path)

        # Get the height and width from the user input
        height, width = height_width.split()
        height = int(height)
        width = int(width)

        # Get the default settings for the model chosen
        cfg_scale, sampler_name, clip_skip = utils.get_model_settings(model_name)

        acknowledgement = await ctx.respond(content=f"Getting lyrics:\n**Song:** {song}\n**Artist:** {artist}")
        fixed_lyrics = get_lyrics(song, artist)
        if fixed_lyrics is None:
            await acknowledgement.edit_original_response(
                content="Lyrics not found. Please check your spelling try again.")
            return
        await acknowledgement.edit_original_response(
            content=f"Getting lyrics:\n**Song:** {song}\n**Artist:** {artist}\nInterpreting lyrics...")
        prompt = gpt_integration(fixed_lyrics)
        if prompt is None:
            await acknowledgement.edit_original_response(content="ChatGPT did not respond or failed, try again.")
            return
        negative_prompt = ""

        # get a funny message
        funny_text = utils.funny_message()

        await acknowledgement.edit_original_response(
            content=f"**{funny_text}**\nGenerating {num_images} images for you!")
        # Send the request to the queue
        await core.queueHandler.add_request(funny_text, acknowledgement, "txt2img", prompt, negative_prompt,
                                            model_path, num_images, height, width, steps, cfg_scale, sampler_name,
                                            clip_skip)
        print(f"Added request to queue: {prompt}, {negative_prompt}, {num_images}, {height}, {width}, {steps},"
              f" {cfg_scale}, {sampler_name}")


def setup(bot):
    bot.add_cog(MusicInterpreterCog(bot))
