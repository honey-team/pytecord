<p> <img src="logo.png" width="250" alt="logo"/></p>

# Dispy

![version](https://img.shields.io/badge/version-0.1b-informational?style=flat) ![project language](https://img.shields.io/badge/lang-python-informational) ![minimal version](https://img.shields.io/badge/minimal_python_version-3.8-informational)

## Download stable version
```
# Windows/Mac Os/Ubuntu
pip install disspy
```

## Links
<p><a href="https://pypi.org/project/disspy">https://pypi.org/project/disspy</a> - Project site on PyPi</p>
<p><a href="https://dispydocs.herokuapp.com/">https://dispydocs.herokuapp.com/</a> - Site with docs for package</p>

## Using

### Creating and running bot

```python
import disspy

bot = disspy.DisBot(token="YOUR_TOKEN")

bot.run()
```

### bot.on("ready")

```python
import disspy

bot = disspy.DisBot(token="YOUR_TOKEN")


@bot.on("ready")
async def on_ready():
    print("Ready!")


bot.run()
```

### bot.on("messagec")

```python
import disspy

bot = disspy.DisBot(token="YOUR_TOKEN")


@bot.on("messagec")
async def on_messagec(message):
    await message.channel.send("Test!")


bot.run()
```
