#!/usr/bin/env python3
from os import path, DirEntry
import os
import sys
import math
import time
import gpiod
import calendar
from datetime import date
from datetime import datetime
import re
from enum import Enum


from PIL import Image, ImageDraw, ImageFont, ImageFilter
from inky.inky_ac073tc1a import Inky, BLACK, WHITE, GREEN, RED, YELLOW, ORANGE, BLUE

saturation = 0.5
canvasSize = (800, 480)
color_palette = Inky.DESATURATED_PALETTE

tmpfs_path = "/dev/shm/"

# font file path(Adjust or change whatever you want)
os.chdir('/home/pi/weather-impression')
project_root = os.getcwd()

unit_imperial = "imperial"

color_map = {
    '01d':ORANGE, # clear sky
    '01n':YELLOW,
    '02d':BLACK, # few clouds
    '02n':BLACK,
    '03d':BLACK, # scattered clouds
    '03n':BLACK,
    '04d':BLACK, # broken clouds
    '04n':BLACK,
    '09d':BLACK, # shower rain
    '09n':BLACK,
    '10d':BLUE,  # rain
    '10n':BLUE, 
    '11d':RED,   # thunderstorm
    '11n':RED,
    '13d':BLUE,  # snow
    '13n':BLUE, 
    '50d':BLACK, # fog
    '50n':BLACK,
    'sunrise':BLACK,
    'sunset':BLACK
}
# icon name to weather icon mapping
icon_map = {
    '01d':u'', # clear sky
    '01n':u'',
    '02d':u'', # few clouds
    '02n':u'',
    '03d':u'', # scattered clouds
    '03n':u'',
    '04d':u'', # broken clouds
    '04n':u'',
    '09d':u'', # shower rain
    '09n':u'',
    '10d':u'', # rain
    '10n':u'',
    '11d':u'', # thunderstorm
    '11n':u'',
    '13d':u'', # snow
    '13n':u'',
    '50d':u'', # fog
    '50n':u'',

    'clock0':u'', # same as 12
    'clock1':u'',
    'clock2':u'',
    'clock3':u'',
    'clock4':u'',
    'clock5':u'',
    'clock6':u'',
    'clock7':u'',
    'clock8':u'',
    'clock9':u'',
    'clock10':u'',
    'clock11':u'',
    'clock12':u'',

    'celsius':u'',
    'fahrenheit':u'',
    'sunrise':u'',
    'sunset':u''
}

#empty structure
class forecastInfo:
    pass

class weatherInfomation(object):
    def __init__(self):
        #load configuration from config.txt using configparser
        import configparser
        self.config = configparser.ConfigParser()
        try:
            self.config.read_file(open(project_root + '/config.txt'))
            self.lat = self.config.get('openweathermap', 'LAT', raw=False)
            self.lon = self.config.get('openweathermap', 'LON', raw=False)
            self.mode = self.config.get('openweathermap', 'mode', raw=False)
            self.forecast_interval = self.config.get('openweathermap', 'FORECAST_INTERVAL', raw=False)
            self.api_key = self.config.get('openweathermap', 'API_KEY', raw=False)
            # API document at https://openweathermap.org/api/one-call-api
            self.unit = self.config.get('openweathermap', 'TEMP_UNIT', raw=False)
            self.cold_temp = float(self.config.get('openweathermap', 'cold_temp', raw=False))
            self.hot_temp = float(self.config.get('openweathermap', 'hot_temp', raw=False))
            self.forecast_api_uri = 'https://api.openweathermap.org/data/3.0/onecall?&lat=' + self.lat + '&lon=' + self.lon +'&appid=' + self.api_key + '&exclude=daily'
            if(self.unit == 'imperial'):
                self.forecast_api_uri = self.forecast_api_uri + "&units=imperial"
            else:
                self.forecast_api_uri = self.forecast_api_uri + "&units=metric"
            self.loadWeatherData()
        except:
            self.one_time_message = "Configuration file is not found or settings are wrong.\nplease check the file : " + project_root + "/config.txt\n\nAlso check your internet connection."
            return

        # load one time messge and remove it from the file. one_time_message can be None.
        try:
            self.one_time_message = self.config.get('openweathermap', 'one_time_message', raw=False)
            self.config.set("openweathermap", "one_time_message", "")
            # remove it.
            with open(project_root + '/config.txt', 'w') as configfile:
                self.config.write(configfile)
        except:
            self.one_time_message = ""
            pass

    def loadWeatherData(self):
        import requests
        self.weatherInfo = requests.get(self.forecast_api_uri).json()


class fonts(Enum):
    thin = project_root + "/fonts/Roboto-Thin.ttf"
    light =  project_root + "/fonts/Roboto-Light.ttf"
    normal = project_root + "/fonts/Roboto-Black.ttf"
    icon = project_root + "/fonts/weathericons-regular-webfont.ttf"

def get_font(type, fontsize=12):
    return ImageFont.truetype(type.value, fontsize)

def get_font_color(temp, wi):
    if temp < wi.cold_temp:
        return (0,0,255)
    if temp > wi.hot_temp:
        return (255,0,0)
    return get_display_color(BLACK)

def get_temperature_unit_icon(unit):
    if(unit == unit_imperial):
        return icon_map['fahrenheit']
    
    return icon_map['celsius']

# return rgb in 0 ~ 255
def get_display_color(color):
    return tuple(color_palette[color])

def get_temperature_string(temp):
    formatted_str = "%0.0f" % temp
    if formatted_str == "-0":
        return "0"
    else:
        return formatted_str

# return color rgb in 0 ~ 1.0 scale
def get_graph_color(color):
    r = color_palette[color][0] / 255
    g = color_palette[color][1] / 255
    b = color_palette[color][2] / 255
    return (r,g,b)

# draw current weather and forecast into canvas
def draw_weather(wi, cv):
    draw = ImageDraw.Draw(cv)
    width, height = cv.size
    margin_x = 40
    margin_y = 20

    # one time message
    if hasattr( wi, "weatherInfo") == False:
        draw.rectangle((0, 0, width, height), fill=get_display_color(ORANGE))
        draw.text((20, 70), u"", get_display_color(BLACK), anchor="lm", font=get_font(fonts.icon, fontsize=130))
        draw.text((150, 80), "Weather information is not available at this time.", get_display_color(BLACK), anchor="lm", font=get_font(fonts.normal, fontsize=18) )
        draw.text((width / 2, height / 2), wi.one_time_message, get_display_color(BLACK), anchor="mm", font=get_font(fonts.normal, fontsize=16) )
        return

    temp_cur = wi.weatherInfo[u'current'][u'temp']
    temp_cur_feels = wi.weatherInfo[u'current'][u'feels_like']
    icon = str(wi.weatherInfo[u'current'][u'weather'][0][u'icon'])
    description = wi.weatherInfo[u'current'][u'weather'][0][u'description']
    #humidity = wi.weatherInfo[u'current'][u'humidity']
    pressure = wi.weatherInfo[u'current'][u'pressure']
    epoch = int(wi.weatherInfo[u'current'][u'dt'])
    #snow = wi.weatherInfo[u'current'][u'snow']
    date_str = time.strftime("%B %-d", time.localtime(epoch))
    weekday_str = time.strftime("%a", time.localtime(epoch))
    #weekDayNumber = time.strftime("%w", time.localtime(epoch))

    # date 
    draw.text((margin_x, margin_y), date_str, get_display_color(BLACK),font=get_font(fonts.normal, fontsize=64))
    draw.text((width - margin_x, margin_y), weekday_str, get_display_color(BLACK), anchor="ra", font=get_font(fonts.normal, fontsize=64))

    offset_x = margin_x
    offset_y = margin_y + 64

    # Draw temperature string
    temp_offset_x = 30 
    temperature_text_size = draw.textsize(get_temperature_string(temp_cur), font=get_font(fonts.normal, fontsize=120))
    if(temperature_text_size[0] < 71):
        # when the temp string is a bit short.
        temp_offset_x = 55

    draw.text((temp_offset_x + offset_x, offset_y), get_temperature_string(temp_cur), get_font_color(temp_cur, wi),font=get_font(fonts.normal, fontsize=120))
    draw.text((offset_x + temperature_text_size[0] + temp_offset_x + 10, offset_y + 120), get_temperature_unit_icon(wi.unit), get_font_color(temp_cur, wi), anchor="ld", font=get_font(fonts.icon, fontsize=80))
    # humidity
    # draw.text((width - 8, 270 + offsetY), str(humidity) + "%", getDisplayColor(BLACK), anchor="rs",font =getFont(fonts.light,fontsize=24))

    # draw current weather icon
    draw.text((width / 2 + 60, offset_y + 150), icon_map[icon], get_display_color(color_map[icon]), anchor="lb",font=get_font(fonts.icon, fontsize=160))
    draw.text((width - margin_x, offset_y), description, get_display_color(BLACK), anchor="ra", font=get_font(fonts.light,fontsize=24))

    """
    # When alerts are in effect, show it to forecast area.
    if wi.mode == '1' and u'alerts' in wi.weatherInfo:
        alertInEffectString = time.strftime('%B %-d, %H:%m %p', time.localtime(wi.weatherInfo[u'alerts'][0][u'start']))

        # remove "\n###\n" and \n\n
        desc = wi.weatherInfo[u'alerts'][0][u'description'].replace("\n###\n", '')
        desc = desc.replace("\n\n", '')
        desc = desc.replace("https://", '') # remove https://
        desc = re.sub(r"([A-Za-z]*:)", "\n\g<1>", desc)
        desc = re.sub(r'((?=.{90})(.{0,89}([\.[ ]|[ ]))|.{0,89})', "\g<1>\n", desc)
        desc = desc.replace("\n\n", '')

        draw.text((5 + offsetX , 215), wi.weatherInfo[u'alerts'][0][u'event'].capitalize() , getDisplayColor(RED),anchor="la", font =getFont(fonts.light,fontsize=24))
        draw.text((5 + offsetX , 240), alertInEffectString + "/" + wi.weatherInfo[u'alerts'][0][u'sender_name'] , getDisplayColor(BLACK), font=getFont(fonts.normal, fontsize=12))

        draw.text((5 + offsetX, 270), desc, getDisplayColor(RED),anchor="la", font =getFont(fonts.normal, fontsize=14))
        return
    """
    
    offset_y += 120

    # feels like
    draw.text((offset_x, offset_y), "Feels like", get_display_color(BLACK),font=get_font(fonts.light,fontsize=24))
    draw.text((offset_x, offset_y + 24), get_temperature_string(temp_cur_feels), get_font_color(temp_cur_feels, wi),font =get_font(fonts.normal, fontsize=50))
    feels_like_text_size = draw.textsize(get_temperature_string(temp_cur_feels), font=get_font(fonts.normal, fontsize=50))
    draw.text((offset_x + feels_like_text_size[0] + 20, offset_y + 24 + 50), get_temperature_unit_icon(wi.unit), get_font_color(temp_cur_feels, wi), anchor="lb", font=get_font(fonts.icon,fontsize=50))

    # Pressure
    draw.text((offset_x + feels_like_text_size[0] + 100, offset_y), "Pressure", get_display_color(BLACK),font=get_font(fonts.light,fontsize=24))
    draw.text((offset_x + feels_like_text_size[0] + 100, offset_y + 24), "%d" % pressure, get_display_color(BLACK),font=get_font(fonts.normal, fontsize=50))
    pressure_text_size = draw.textsize("%d" % pressure, font=get_font(fonts.normal, fontsize=50))
    draw.text((offset_x + feels_like_text_size[0] + pressure_text_size[0] + 100, offset_y + 24 + 50), "hPa", get_display_color(BLACK), anchor="ld", font=get_font(fonts.normal, fontsize=22))
    
    """
    # Graph mode
    if wi.mode == '2':
        import matplotlib.pyplot as plt
        from matplotlib import font_manager as fm, rcParams
        import numpy as np
        forecast_range = 47
        graph_height = 1.1
        graph_width = 8.4
        xarray = []
        tempArray = []
        feelsArray = []
        pressureArray = []
        try:
            for fi in range(forecast_range):
                finfo = forecastInfo()
                finfo.time_dt  = wi.weatherInfo[u'hourly'][fi][u'dt']
                finfo.time     = time.strftime('%-I %p', time.localtime(finfo.time_dt))
                finfo.temp     = wi.weatherInfo[u'hourly'][fi][u'temp']
                finfo.feels_like     = wi.weatherInfo[u'hourly'][fi][u'feels_like']
                finfo.humidity = wi.weatherInfo[u'hourly'][fi][u'humidity']
                finfo.pressure = wi.weatherInfo[u'hourly'][fi][u'pressure']
                finfo.icon     = wi.weatherInfo[u'hourly'][fi][u'weather'][0][u'icon']
                # print(wi.weatherInfo[u'hourly'][fi][u'snow'][u'1h']) # mm  / you may get 8 hours maximum
                xarray.append(finfo.time_dt)
                tempArray.append(finfo.temp)
                feelsArray.append(finfo.feels_like)
                pressureArray.append(finfo.pressure)
        except IndexError:
            # The weather forecast API is supposed to return 48 forecasts, but it may return fewer than 48.
            errorMessage = "Weather API returns limited hourly forecast(" + str(len(xarray)) + ")"
            draw.text((width - 10, height - 2), errorMessage, getDisplayColor(ORANGE), anchor="ra", font=getFont(fonts.normal, fontsize=12))
            pass
        
        fig = plt.figure()
        fig.set_figheight(graph_height)
        fig.set_figwidth(graph_width)
        plt.plot(xarray, pressureArray, linewidth=3, color=getGraphColor(RED)) # RGB in 0~1.0
        #plt.plot(xarray, pressureArray)
        #annot_max(np.array(xarray),np.array(tempArray))
        #annot_max(np.array(xarray),np.array(pressureArray))
        plt.axis('off')
        ax = plt.gca()
        airPressureMin = 990
        airPressureMax = 1020
        if min(pressureArray) < airPressureMin - 2:
            airPressureMin = min(pressureArray) + 2
        if max(pressureArray) > airPressureMax - 2:
            airPressureMax = max(pressureArray) + 2

        plt.ylim(airPressureMin,airPressureMax)

        plt.savefig(tmpfs_path + 'pressure.png', bbox_inches='tight', transparent=True)
        tempGraphImage = Image.open(tmpfs_path + "pressure.png")
        cv.paste(tempGraphImage, (-35, 330), tempGraphImage)

        # draw temp and feels like in one figure
        fig = plt.figure()
        fig.set_figheight(graph_height)
        fig.set_figwidth(graph_width)
        plt.plot(xarray, feelsArray, linewidth=3, color=getGraphColor(GREEN), linestyle=':') # RGB in 0~1.0
        plt.axis('off')
        plt.plot(xarray, tempArray, linewidth=3, color=getGraphColor(BLUE))

        for idx in range(1, len(xarray)):
            h = time.strftime('%-I', time.localtime(xarray[idx]))
            if h == '0' or h == '12':
                plt.axvline(x=xarray[idx], color='black', linestyle=':')
                posY = np.array(tempArray).max() + 1
                plt.text(xarray[idx-1], posY, time.strftime('%p', time.localtime(xarray[idx])))
        plt.axis('off')
        plt.savefig(tmpfs_path+'temp.png', bbox_inches='tight',  transparent=True)
        tempGraphImage = Image.open(tmpfs_path+"temp.png")
        cv.paste(tempGraphImage, (-35, 300), tempGraphImage)

        # draw label
        draw.rectangle((5, 430, 20, 446), fill=getDisplayColor(RED))
        draw.text((15 + offsetX, 428), "Pressure", getDisplayColor(BLACK),font=getFont(fonts.normal, fontsize=16))

        draw.rectangle((135, 430, 150, 446), fill=getDisplayColor(BLUE))
        draw.text((145 + offsetX, 428), "Temp", getDisplayColor(BLACK),font=getFont(fonts.normal, fontsize=16))

        draw.rectangle((265, 430, 280, 446), fill=getDisplayColor(GREEN))
        draw.text((275 + offsetX, 428), "Feels like", getDisplayColor(BLACK),font=getFont(fonts.normal, fontsize=16))
        return

    # Sunrise / Sunset mode
    if wi.mode == '3':
        sunrise = wi.weatherInfo['current']['sunrise']
        sunset = wi.weatherInfo['current']['sunset']

        sunriseFormatted = datetime.fromtimestamp(sunrise).strftime("%#I:%M %p")
        sunsetFormatted = datetime.fromtimestamp(sunset).strftime("%#I:%M %p")

        #print([sunriseFormatted, sunsetFormatted])

        columnWidth = width / 2
        textColor = (50,50,50)
        # center = column width / 2 - (text_width * .5)
        # measure sunrise
        sunrise_width, _ = getFont(fonts.normal, fontsize=16).getsize("Sunrise")
        sunriseXOffset = (columnWidth/2) - (sunrise_width * .5)
        
        sunriseFormatted_width, _ = getFont(fonts.normal, fontsize=12).getsize(sunriseFormatted)
        sunriseFormattedXOffset = (columnWidth/2) - (sunriseFormatted_width * .5)

        sunriseIcon_width, _ = getFont(fonts.icon, fontsize=90).getsize(iconMap['sunrise'])
        sunriseIconXOffset = (columnWidth/2) - (sunriseIcon_width * .5)

        draw.text((sunriseFormattedXOffset, offsetY + 220), sunriseFormatted,textColor,anchor="la", font =getFont(fonts.normal, fontsize=12))
        draw.text((sunriseIconXOffset, offsetY + 90), iconMap['sunrise'], getDisplayColor(colorMap['sunrise']), anchor="la",font =getFont(fonts.icon, fontsize=90))
        draw.text((sunriseXOffset,  offsetY + 200), "Sunrise", textColor,anchor="la", font =getFont(fonts.normal, fontsize=16))

        sunset_width, _ = getFont(fonts.normal, fontsize=16).getsize("sunset")
        sunsetXOffset = columnWidth + (columnWidth/2) - (sunset_width * .5)
        
        sunsetFormatted_width, _ = getFont(fonts.normal, fontsize=12).getsize(sunsetFormatted)
        sunsetFormattedXOffset = columnWidth + (columnWidth/2) - (sunsetFormatted_width * .5)

        sunsetIcon_width, _ = getFont(fonts.icon, fontsize=90).getsize(iconMap['sunset'])
        sunsetIconXOffset = columnWidth + (columnWidth/2) - (sunsetIcon_width * .5)

        draw.text((sunsetFormattedXOffset, offsetY + 220), sunsetFormatted,textColor,anchor="la", font =getFont(fonts.normal, fontsize=12))
        draw.text((sunsetIconXOffset, offsetY + 90), iconMap['sunset'], getDisplayColor(colorMap['sunset']), anchor="la",font =getFont(fonts.icon, fontsize=90))
        draw.text((sunsetXOffset,  offsetY + 200), "Sunset", textColor,anchor="la", font =getFont(fonts.normal, fontsize=16))

        return
    
    if wi.mode == '4':
        import matplotlib.pyplot as plt
        from matplotlib import font_manager as fm, rcParams
        import matplotlib
        import numpy as np
        # import datetime

        def minutes_since(timestamp):
            dt = datetime.fromtimestamp(timestamp)
            timestamp_minutes_since_midnight = dt.hour * 60 + dt.minute
            return timestamp_minutes_since_midnight

        # icon font setup
        icon_font = getFont(fonts.icon, fontsize=12)
        icon_prop = fm.FontProperties(fname=icon_font.path)
        text_font = getFont(fonts.normal, fontsize=12)
        text_prop = fm.FontProperties(fname=text_font.path)

        graph_height = 1.1
        graph_width = 8.4

        x = [i for i in range(24)]
        # y = [math.sin(math.pi * i / 12) for i in x]
        y = [math.cos((i / 12 - 1) * math.pi) for i in x]

        fig = plt.figure()
        fig.set_figheight(graph_height)
        fig.set_figwidth(graph_width)

        plt.xlim(0, 23)
        plt.ylim(-1.2, 1.2)
        # add labels and title
        # plt.xlabel("Hour of Day")
        # plt.ylabel("Sun Elevation")
        plt.title("")

        # add sunrise and sunset lines
        sunrise_timestamp = wi.weatherInfo['current']['sunrise']
        sunset_timestamp = wi.weatherInfo['current']['sunset']
        sunrise_time = minutes_since(sunrise_timestamp)
        sunset_time = minutes_since(sunset_timestamp)
        sunrise_hour = sunrise_time / 60
        sunset_hour = sunset_time / 60
        sunriseFormatted = datetime.fromtimestamp(sunrise_timestamp).strftime("%#I:%M %p")
        sunsetFormatted = datetime.fromtimestamp(sunset_timestamp).strftime("%#I:%M %p")

        plt.axvline(x=sunrise_hour, color="blue", linestyle="--")
        plt.axvline(x=sunset_hour, color="blue", linestyle="--")

        plt.text(sunrise_hour-.35, 1.35, iconMap['sunrise'], fontproperties=icon_prop, ha="right", va="top", color=getGraphColor(YELLOW))
        plt.text(sunrise_hour-.3, 1.3, iconMap['sunrise'], fontproperties=icon_prop, ha="right", va="top", color=getGraphColor(BLUE))

        plt.text(sunset_hour+.35, 1.35, iconMap['sunset'], fontproperties=icon_prop, ha="left", va="top", color=getGraphColor(YELLOW))
        plt.text(sunset_hour+.3, 1.3, iconMap['sunset'], fontproperties=icon_prop, ha="left", va="top", color=getGraphColor(BLUE))
        plt.text(sunrise_hour-.3, .8, sunriseFormatted, ha="right", va="top", fontproperties=text_prop, rotation="horizontal", color=getGraphColor(BLUE))
        plt.text(sunset_hour+.3, .8, sunsetFormatted, ha="left", va="top", fontproperties=text_prop, rotation="horizontal", color=getGraphColor(BLUE))

        normal = getFont(fonts.normal, fontsize=12)
        plt.rcParams['font.family'] = normal.getname()

        plt.plot(x, y, linewidth=3, color=getGraphColor(RED)) # RGB in 0~1.0
        #plt.plot(xarray, pressureArray)
        #annot_max(np.array(xarray),np.array(tempArray))
        #annot_max(np.array(xarray),np.array(pressureArray))
        plt.axis('off')

        plt.savefig(tmpfs_path + 'day.png', bbox_inches='tight', transparent=True)
        tempGraphImage = Image.open(tmpfs_path+"day.png")
        cv.paste(tempGraphImage, (-35, 300), tempGraphImage)

        return
    """

    offset_y += 24 + 50
    
    forecast_interval_hrs = int(wi.forecast_interval)
    forecast_range = 4
    for fi in range(forecast_range):
        finfo = forecastInfo()
        finfo.time_dt  = wi.weatherInfo[u'hourly'][fi * forecast_interval_hrs + forecast_interval_hrs][u'dt']
        finfo.time     = time.strftime('%-I %p', time.localtime(finfo.time_dt))
        finfo.timeIn12h = time.strftime('clock%-I', time.localtime(finfo.time_dt))
        #finfo.ampm     = time.strftime('%p', time.localtime(finfo.time_dt))
        #finfo.time     = time.strftime('%-I', time.localtime(finfo.time_dt))
        finfo.timePfx  = time.strftime('%p', time.localtime(finfo.time_dt))
        finfo.temp     = wi.weatherInfo[u'hourly'][fi * forecast_interval_hrs + forecast_interval_hrs][u'temp']
        finfo.feels_like = wi.weatherInfo[u'hourly'][fi * forecast_interval_hrs + forecast_interval_hrs][u'feels_like']
        finfo.humidity = wi.weatherInfo[u'hourly'][fi * forecast_interval_hrs + forecast_interval_hrs][u'humidity']
        finfo.pressure = wi.weatherInfo[u'hourly'][fi * forecast_interval_hrs + forecast_interval_hrs][u'pressure']
        finfo.icon     = wi.weatherInfo[u'hourly'][fi * forecast_interval_hrs + forecast_interval_hrs][u'weather'][0][u'icon']
        finfo.description = wi.weatherInfo[u'hourly'][fi * forecast_interval_hrs + forecast_interval_hrs][u'weather'][0][u'description'] # show the first 

        column_width = (width - 2 * margin_x) / forecast_range
        textColor = (50, 50, 50)

        draw.text((offset_x + (column_width / 2) + (fi * column_width), offset_y), icon_map[finfo.icon], get_display_color(color_map[finfo.icon]), anchor="ma", font=get_font(fonts.icon, fontsize=100))
        draw.text((offset_x + (column_width / 2) + (fi * column_width),  offset_y + 100 + 10), finfo.description, textColor, anchor="ma", font=get_font(fonts.normal, fontsize=24))
        draw.text((offset_x + (column_width / 2) + (fi * column_width), offset_y + 100 + 10 + 24), ("%2.1f" % finfo.temp), textColor, anchor="ma", font=get_font(fonts.normal, fontsize=18))
        draw.text((offset_x + (column_width / 2) + (fi * column_width), offset_y + 100 + 10 + 24 + 18), finfo.time,textColor, anchor="ma", font=get_font(fonts.normal, fontsize=18))
        

def annot_max(x,y, ax=None):
    xmax = x[np.argmax(y)]
    ymax = y.max()
    maxTime = time.strftime('%b %-d,%-I%p', time.localtime(xmax))
    text= maxTime + " {:.1f}C".format(ymax)
    if not ax:
        ax=plt.gca()
    bbox_props = dict(boxstyle="square,pad=0.3", fc="w", ec="k", lw=0.72)
    arrowprops=dict(arrowstyle="->",connectionstyle="angle,angleA=0,angleB=60")
    kw = dict(xycoords='data',textcoords="axes fraction",
              arrowprops=arrowprops, bbox=bbox_props, ha="right", va="top")

    fpath = "/home/pi/weather-impression/fonts/Roboto-Black.ttf"
    prop = fm.FontProperties(fname=fpath)
    ax.annotate(text, xy=(xmax, ymax), xytext=(0.93,1.56), fontproperties=prop, **kw)

def init_gpio():
    chip = gpiod.chip(0) # 0 chip 
    pin = 4
    gpiod_pin = chip.get_line(pin)
    config = gpiod.line_request()
    config.consumer = "Blink"
    config.request_type = gpiod.line_request.DIRECTION_OUTPUT
    gpiod_pin.request(config)
    return gpiod_pin

def update():
    gpio_pin = init_gpio()
    gpio_pin.set_value(1)

    wi = weatherInfomation()
    cv = Image.new("RGB", canvasSize, get_display_color(WHITE))
    draw_weather(wi, cv)

    inky = Inky()
    inky.set_image(cv, saturation=saturation)
    inky.show()

    gpio_pin.set_value(0)

if __name__ == "__main__":
    update()
