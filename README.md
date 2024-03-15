# PolyPlay 

Playback control module for polybar.

## Features:

- Scrolling text to display the track and artist name.
- Controlls allowing you to play/pause, skip and go previous tracks.
- Cycle between active player programs by scrolling on the displayed text.

## Using Polyplay 

1. Clone the repo
2. In your polybar .ini config file, add the following (example):

```.ini
[module/polyplay]
type = custom/script
tail = true
format = <label>
exec = </path/to/your/downloaded/polyplay.py>
```

3. `chmod +x /path/to/your/downloaded/polyplay.py` 
4. Modify parameters in the `class Config` to your liking. Read the comments before modifying variables.

## Dependencies:

### Python 3.11

Development is done on Python version `3.11.7` 


### Playerctl

Currently uses `playerctl` commands to control the players.

In the future, planning to explore using `dbus` instead.


### Fonts

To display non-English characters, you should install relevant fonts. EG: Sarasa Mono CL for JP, CN, KR characters.

As the module's length is determined by the length of a string, and not a set amount of pixels, the font you use will have an effect on the length of this module. Non english characters tends to be larger and takes up more horizontal space, this will cause the length of the module to fluctuate. The way around this is to configure the individual font size in your polybar font config. Typically, you will have to set the non-English font fontsize to be much smaller than the English font to make each character take up the same amount of sapce.

