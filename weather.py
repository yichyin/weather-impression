#!/usr/bin/env python3
from os import path, DirEntry
import os
import sys
import math
import time
import calendar
from datetime import date
from datetime import datetime
import re
from enum import Enum


from PIL import Image, ImageDraw, ImageFont, ImageFilter
from inky.inky_uc8159 import Inky, BLACK, WHITE, GREEN, RED, YELLOW, ORANGE, BLUE, SATURATED_PALETTE

saturation = 0.5
canvasSize = (600, 448)

# font file path(Adjust or change whatever you want)
os.chdir('/home/pi/weather-impression')
project_root = os.getcwd()

dayOfWeekColor = {
    '0':(0, 0, 0),
    '1':(255, 255, 255),
    '2':(0, 255, 0),
    '3':(0, 0, 255),
    '4':(255, 0, 0),
    '5':(255, 255, 0),
    '6':(255, 140, 0),
}

colorMap = {
    '01d':(255,140,0), # clear sky
    '01n':(255, 255, 0),
    '02d':(0,0,0), # few clouds
    '02n':(0,0,0),
    '03d':(0,0,0), # scattered clouds
    '03n':(0,0,0),
    '04d':(0,0,0), # broken clouds
    '04n':(0,0,0),
    '09d':(0,0,0), # shower rain
    '09n':(0,0,0),
    '10d':(0,0,255), # rain
    '10n':(0,0,255),
    '11d':(255,0,0), # thunderstorm
    '11n':(255,0,0),
    '13d':(0,0,255), # snow
    '13n':(0,0,255),
    '50d':(0,0,0), # fog
    '50n':(0,0,0),
}
# icon name to weather icon mapping
iconMap = {
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

    'celsius':u''
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
            self.forecast_api_uri = 'https://api.openweathermap.org/data/2.5/onecall?&lat=' + self.lat + '&lon=' + self.lon +'&appid=' + self.api_key + '&exclude=daily&units=metric'
            self.loadWeatherData()
        except:
            self.one_time_message = "Configuration file is not found or settings are wrong.\n\nplease check the file : " + project_root + "/config.txt"
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
    icon = project_root + "fonts/weathericons-regular-webfont.ttf"

def getFont(type, fontsize=12):
    return ImageFont.truetype(type.value, fontsize)

def getFontColor(temp):
    if temp < -10:
        return (0,0,255)
    if temp > 28:
        return (255,0,0)
    return (0,0,0)

def getDisplayColor(color):
    return tuple(SATURATED_PALETTE[color])

def getGraphColor(color):
    r = SATURATED_PALETTE[color][0] / 255
    g = SATURATED_PALETTE[color][1] / 255
    b = SATURATED_PALETTE[color][2] / 255
    return (r,g,b)

# draw current weather and forecast into canvas
def drawWeather(wi, cv):
    draw = ImageDraw.Draw(cv)
    width, height = cv.size

    # one time message
    if hasattr( wi, "weatherInfo") == False:
        draw.text((width / 2, height / 2), wi.one_time_message, (255,0,0), anchor="mm", font=getFont(fonts.normal, fontsize=22) )
        return
    draw.text((width - 10, 2), wi.one_time_message, (0,0,0), anchor="ra", font=getFont(fonts.normal, fontsize=12))
    
    temp_cur = wi.weatherInfo[u'current'][u'temp']
    temp_cur_feels = wi.weatherInfo[u'current'][u'feels_like']
    icon = str(wi.weatherInfo[u'current'][u'weather'][0][u'icon'])
    description = wi.weatherInfo[u'current'][u'weather'][0][u'description']
    humidity = wi.weatherInfo[u'current'][u'humidity']
    pressure = wi.weatherInfo[u'current'][u'pressure']
    epoch = int(wi.weatherInfo[u'current'][u'dt'])
    dateString = time.strftime("%B %-d", time.localtime(epoch))
    weekDayString = time.strftime("%a", time.localtime(epoch))
    weekDayNumber = time.strftime("%w", time.localtime(epoch))

    # date 
    draw.text((15 , 5), dateString, (0,0,0),font=getFont(fonts.normal, fontsize=64))
    draw.text((width - 8 , 5), weekDayString, (0,0,0), anchor="ra", font =getFont(fonts.normal, fontsize=64))

    offsetX = 10
    offsetY = 40

    # draw date string
    draw.text((5 + offsetX , 35 + offsetY), "Temperature", (0,0,0),font =getFont(fonts.light,fontsize=24))
    draw.text((0 + offsetX, 50 + offsetY), "%2.0f" % temp_cur, getFontColor(temp_cur),font =getFont(fonts.normal, fontsize=120))
    temperatureTextSize = draw.textsize("%2.0f" % temp_cur, font =getFont(fonts.normal, fontsize=120))
    draw.text((temperatureTextSize[0] + 10 + offsetX, 85 + offsetY), iconMap['celsius'], getFontColor(temp_cur), anchor="la", font =getFont(fonts.icon, fontsize=80))
    # humidity
    # draw.text((width - 8, 270 + offsetY), str(humidity) + "%", (0,0,0), anchor="rs",font =getFont(fonts.light,fontsize=24))

    # draw current weather icon
    draw.text((440 + offsetX, 40 + offsetY), iconMap[icon], colorMap[icon], anchor="ma",font=getFont(fonts.icon, fontsize=160))

    draw.text((width - 8, 35 + offsetY), description, (0,0,0), anchor="ra", font =getFont(fonts.light,fontsize=24))

    offsetY = 210
    
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

        draw.text((5 + offsetX , 215), wi.weatherInfo[u'alerts'][0][u'event'].capitalize() , (255,0,0),anchor="la", font =getFont(fonts.light,fontsize=24))
        draw.text((5 + offsetX , 240), alertInEffectString + "/" + wi.weatherInfo[u'alerts'][0][u'sender_name'] , (0,0,0), font=getFont(fonts.normal, fontsize=12))

        draw.text((5 + offsetX, 270), desc, (255,0,0),anchor="la", font =getFont(fonts.normal, fontsize=14))
        return
    # feels like
    draw.text((5 + offsetX , 175 + 40), "Feels like", (0,0,0),font =getFont(fonts.light,fontsize=24))
    draw.text((10 + offsetX, 200 + 40), "%2.0f" % temp_cur_feels,getFontColor(temp_cur_feels),font =getFont(fonts.normal, fontsize=50))
    feelslikeTextSize = draw.textsize("%2.0f" % temp_cur_feels, font =getFont(fonts.normal, fontsize=50))
    draw.text((feelslikeTextSize[0] + 20 + offsetX, 200 + 40), iconMap['celsius'], getFontColor(temp_cur_feels), anchor="la", font=getFont(fonts.icon,fontsize=50))

    # Pressure
    draw.text((feelslikeTextSize[0] + 85 + offsetX , 175 + 40), "Pressure", (0,0,0),font =getFont(fonts.light,fontsize=24))
    draw.text((feelslikeTextSize[0] + 90 + offsetX, 200 + 40), "%d" % pressure, (0,0,0),font =getFont(fonts.normal, fontsize=50))
    pressureTextSize = draw.textsize("%d" % pressure, font =getFont(fonts.normal, fontsize=50))
    draw.text((feelslikeTextSize[0] + pressureTextSize[0] + 95 + offsetX, 224 + 40), "hPa", (0,0,0),font=getFont(fonts.normal, fontsize=22))
    
    # Graph mode
    if wi.mode == '2':
        import matplotlib.pyplot as plt
        from matplotlib import font_manager as fm, rcParams
        import numpy as np
        forecastRange = 47
        graph_height = 1.1
        graph_width = 8.4
        xarray = []
        tempArray = []
        feelsArray = []
        pressureArray = []
        try:
            for fi in range(forecastRange):
                finfo = forecastInfo()
                finfo.time_dt  = wi.weatherInfo[u'hourly'][fi][u'dt']
                finfo.time     = time.strftime('%-I %p', time.localtime(finfo.time_dt))
                finfo.temp     = wi.weatherInfo[u'hourly'][fi][u'temp']
                finfo.feels_like     = wi.weatherInfo[u'hourly'][fi][u'feels_like']
                finfo.humidity = wi.weatherInfo[u'hourly'][fi][u'humidity']
                finfo.pressure = wi.weatherInfo[u'hourly'][fi][u'pressure']
                finfo.icon     = wi.weatherInfo[u'hourly'][fi][u'weather'][0][u'icon']
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
        plt.savefig('pressure.png', bbox_inches='tight', transparent=True)
        tempGraphImage = Image.open("pressure.png")
        cv.paste(tempGraphImage, (-35, 330), tempGraphImage)


        fig = plt.figure()
        fig.set_figheight(graph_height)
        fig.set_figwidth(graph_width)
        plt.plot(xarray, feelsArray, linewidth=1, color=getGraphColor(GREEN), linestyle=':') # RGB in 0~1.0
        plt.axis('off')
        plt.savefig('feels.png', bbox_inches='tight', transparent=True)
        tempGraphImage = Image.open("feels.png")
        cv.paste(tempGraphImage, (-35, 317), tempGraphImage)


        fig = plt.figure()
        fig.set_figheight(graph_height)
        fig.set_figwidth(graph_width)
        plt.plot(xarray, tempArray, linewidth=3, color=getGraphColor(BLUE))

        for idx in range(1, len(xarray)):
            h = time.strftime('%-I', time.localtime(xarray[idx]))
            if h == '0' or h == '12':
                plt.axvline(x=xarray[idx], color='black', linestyle=':')
                posY = np.array(tempArray).max() + 1
                plt.text(xarray[idx-1], posY, time.strftime('%p', time.localtime(xarray[idx])))
        plt.axis('off')
        plt.savefig('temp.png', bbox_inches='tight',  transparent=True)
        tempGraphImage = Image.open("temp.png")
        cv.paste(tempGraphImage, (-35, 300), tempGraphImage)

        # draw label
        draw.rectangle((5, 430, 20, 446), fill=getDisplayColor(RED))
        draw.text((15 + offsetX, 428), "Air pressure", (0,0,0),font =getFont(fonts.normal, fontsize=16))

        draw.rectangle((135, 430, 150, 446), fill=getDisplayColor(BLUE))
        draw.text((145 + offsetX, 428), "Temp", (0,0,0),font =getFont(fonts.normal, fontsize=16))
        return
    

    forecastIntervalHours = int(wi.forecast_interval)
    forecastRange = 4
    for fi in range(forecastRange):
        finfo = forecastInfo()
        finfo.time_dt  = wi.weatherInfo[u'hourly'][fi * forecastIntervalHours + forecastIntervalHours][u'dt']
        finfo.time     = time.strftime('%-I %p', time.localtime(finfo.time_dt))
        finfo.timeIn12h = time.strftime('clock%-I', time.localtime(finfo.time_dt))
        #finfo.ampm     = time.strftime('%p', time.localtime(finfo.time_dt))
        #finfo.time     = time.strftime('%-I', time.localtime(finfo.time_dt))
        finfo.timePfx  = time.strftime('%p', time.localtime(finfo.time_dt))
        finfo.temp     = wi.weatherInfo[u'hourly'][fi * forecastIntervalHours + forecastIntervalHours][u'temp']
        finfo.feels_like = wi.weatherInfo[u'hourly'][fi * forecastIntervalHours + forecastIntervalHours][u'feels_like']
        finfo.humidity = wi.weatherInfo[u'hourly'][fi * forecastIntervalHours + forecastIntervalHours][u'humidity']
        finfo.pressure = wi.weatherInfo[u'hourly'][fi * forecastIntervalHours + forecastIntervalHours][u'pressure']
        finfo.icon     = wi.weatherInfo[u'hourly'][fi * forecastIntervalHours + forecastIntervalHours][u'weather'][0][u'icon']
        finfo.description = wi.weatherInfo[u'hourly'][fi * forecastIntervalHours + forecastIntervalHours][u'weather'][0][u'description'] # show the first 

        columnWidth = width / forecastRange
        textColor = (50,50,50)
        # Clock icon for the time.(Not so nice.)
        #draw.text((20 + (fi * columnWidth),  offsetY + 90), iconMap[finfo.timeIn12h], textColor, anchor="ma",font =ImageFont.truetype(project_root + "fonts/weathericons-regular-webfont.ttf", 35))
        draw.text((30 + (fi * columnWidth), offsetY + 220), finfo.time,textColor,anchor="la", font =getFont(fonts.normal, fontsize=12))
        draw.text((120 + (fi * columnWidth), offsetY + 220), ("%2.1f" % finfo.temp), textColor, anchor="ra", font=getFont(fonts.normal, fontsize=12) )
        
        draw.text(((columnWidth / 2) + (fi * columnWidth),  offsetY + 200), finfo.description, textColor,anchor="ma", font =getFont(fonts.normal, fontsize=16))
        draw.text((70 + (fi * columnWidth), offsetY + 90), iconMap[finfo.icon], colorMap[finfo.icon], anchor="ma",font =getFont(fonts.icon, fontsize=80))

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

def update():
    wi = weatherInfomation()

    cv = Image.new("RGB", canvasSize, (255, 255, 255))
    #cv = cv.rotate(90, expand=True)
    drawWeather(wi, cv)
    #cv.save("test.png")
    #cv = cv.rotate(-90, expand=True)
    inky = Inky()
    inky.set_image(cv, saturation=saturation)
    inky.show()

if __name__ == "__main__":
    update()
