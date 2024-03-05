# MusicInterpreterCog
Example Cog for ImageGenBot that takes a song and artist name, gets the lyrics from Genius and interprets them using ChatGPT.

## Requirements
You will need your own Genius Lyrics API key and OpenAI API key, and obviously ImageGenBot setup.

## Setup
These steps will depend on how you have ImageGenBot setup.  The easiest way to get custom cogs to work is with 
Move music_interpreter_cog.py and music_interpreter_requirements.txt to ImageGenBot/custom_cogs/

Add lines from env.txt to the .env included with ImageGenBot.  Add your Genius Lyrics API key and OpenAI api key to the fields.

Add requirements to requirements.txt or install them manually using:

`pip install -r custom_cogs/music_interpreter_requirements.txt`

## Usage

Type `/interpret` and fill out the Song name and Artist, then (optionally) choose the model name, number of images to generate (up to 4), height and width of the images, and generation steps.


## Disclaimer
The current setup uses about 900 tokens for OpenAI.  The initial context uses ~850.  I would be interested to see if anyone has a more efficient prompt to get a working and good looking prompt from ChatGPT.  With the cost of GPT 3.5 Turbo (the model I have set for the ChatGPT portion), this comes to less than $0.01 per request.
