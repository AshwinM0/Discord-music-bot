import asyncio
from discord.ext import commands
import discord
from datetime import datetime
import pytz
import os
from dotenv import load_dotenv
import requests
from discord import FFmpegPCMAudio
from discord.utils import get
import yt_dlp as youtube_dl
from collections import deque



load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

CHANNELID = os.getenv("CHANNEL_ID")

bot = commands.Bot(command_prefix="<>", intents=discord.Intents.all())

queue = deque([])

def search(query):
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': 'True',  # Do not download playlists
    }
    
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        # Extract information from YouTube search or URL
        try: requests.get(query)
        except: info = ydl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
        else: info = ydl.extract_info(query, download=False)
        #info = ydl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]  # Get the first search result

        # Get the best audio format URL
        audio_url = info.get('url')
        video_title = info.get('title')
        
        #print(f"Video Title: {video_title}")
        #print(f"Audio URL: {audio_url}")
        
        return [video_title, audio_url]

@bot.event
async def on_ready():
    print("The bot is running")
    channel = bot.get_channel(CHANNELID)
    #await channel.send("The bot is ready")

@bot.command()
async def hello(ctx):
    await ctx.send("Hi!")

@bot.command()
async def add(ctx, *arr):
    res = 0
    for i in arr:
        res+=int(i)
    await ctx.send(f"It is {res}")

@bot.command(pass_context=True)
async def join(ctx):
    voiceUtil = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if(voiceUtil == None and ctx.author.voice):
        channel = ctx.author.voice.channel
        await channel.connect()
    elif(ctx.author.voice and voiceUtil and ctx.author.voice.channel!=voiceUtil.channel):
        channel = ctx.author.voice.channel
        await ctx.voice_client.disconnect()
        await channel.connect()
    elif(ctx.author.voice and voiceUtil and ctx.author.voice.channel==voiceUtil.channel):
        await ctx.send("I'm already in your VC")
    elif(ctx.author.voice == None and voiceUtil):
        await ctx.send("I'm already in a vc and you're not")
    else:
        await ctx.send("Join a voice channel idiot")



async def joinToPlay(ctx):
    voiceUtil = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if(voiceUtil == None and ctx.author.voice):
        channel = ctx.author.voice.channel
        await channel.connect()
    elif(ctx.author.voice and voiceUtil and ctx.author.voice.channel!=voiceUtil.channel):
        channel = ctx.author.voice.channel
        await ctx.voice_client.disconnect()
        await channel.connect()
    elif(ctx.author.voice and voiceUtil and ctx.author.voice.channel==voiceUtil.channel):
        print()
    elif(ctx.author.voice == None and voiceUtil):
        await ctx.send("Join the vc")
    else:
        await ctx.send("Join a vc")

@bot.command(pass_context=True)
async def leave(ctx):
    voiceUtil = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if(voiceUtil):
        await ctx.voice_client.disconnect()
    else:
        await ctx.send("I'm not in a VC")

@bot.command()
async def uk(ctx):
    time = pytz.timezone('Europe/London')
    tim1 = datetime.now(time)
    londonTime = tim1.astimezone(pytz.utc)
    await ctx.send(f'{tim1.strftime("%Y-%m-%d %H:%M:%S %Z %z")}')

def clearQueue():
    queue.clear()
    
#(await nextone(ctx) for _ in '_').__anext__()
async def nextone(ctx):
    print("in next one")
    voice = get(bot.voice_clients, guild=ctx.guild)
    FFMPEG_OPTS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
    
    print(queue)
    if len(queue)!=0:
        info, source = search(queue[0])
        queue.popleft()
        voice.play(FFmpegPCMAudio(source, **FFMPEG_OPTS), after=lambda e: asyncio.run_coroutine_threadsafe(nextone(ctx), ctx.bot.loop).result())
    else:
        await asyncio.sleep(120)
        voice = get(bot.voice_clients, guild=ctx.guild)
        if(voice.is_playing()):
            return None
        if len(queue)==0:
            await ctx.send("Nothing was played in the last 2 minutes")
            print("leaving coz queue is empty")
            await leave(ctx)
#after= lambda e: nextone(ctx)

@bot.command()
async def play(ctx, *url):
    
    urlstr = ''

    for i in url:
        urlstr+= (i + " ")
    print(urlstr)
    queue.append(urlstr)
    
    await joinToPlay(ctx)
    voice = get(bot.voice_clients, guild=ctx.guild)
    if(voice.is_playing()):
        await ctx.send("Added to Q")
    else:
        await nextone(ctx)


@bot.command()
async def skip(ctx):
    voiceUtil = get(bot.voice_clients, guild=ctx.guild)
    if(voiceUtil):
        voiceUtil.stop()

@bot.command()
async def stop(ctx):
    voiceUtil = get(bot.voice_clients, guild=ctx.guild)
    clearQueue()
    if(voiceUtil.is_playing()):
        voiceUtil.stop()
    else:
        await ctx.send("Not playing anything rn")

@bot.command()
async def q(ctx):
    res = ''
    for i in queue:
        res += i + '\n'
    
    await ctx.send(res[:-1])
    


bot.run(TOKEN)