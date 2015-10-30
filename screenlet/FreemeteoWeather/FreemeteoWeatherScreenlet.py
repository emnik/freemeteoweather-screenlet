#!/usr/bin/env python
# -*- coding: utf-8 -*-

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

#  Freemeteo Weather Screenlet / Copyright 2010, 2011 Nikiforakis Manos under GPL3
#  Extra translation stuff & design / Copyright 2010 Guido Tabbernuk under GPL3
#  Drawing code : Based on the Default Weather Screenlet
#  UI : Based on Widescape's Weather Konfabulator Widget

import screenlets
from screenlets.options import ColorOption, FontOption, BoolOption, StringOption
import cairo
import string
import time, datetime
import pango
import gtk
import gobject
import threading
import traceback
import urllib2 
import re

# use gettext for translation
import gettext

_ = screenlets.utils.get_translator(__file__)

def tdoc(obj):
	obj.__doc__ = _(obj.__doc__)
	return obj

class Updater(threading.Thread):

	dealingWithData = False
	
	__lock = threading.Lock()

	screenlet = None
	

	def __init__(self, screenlet):
		threading.Thread.__init__(self)
		self.screenlet = screenlet

	def run ( self ):
		if not self.dealingWithData:
			self.dealingWithData = True
			threading.Thread(target=self.__deal_with_data).start()
			

	def __deal_with_data(self):

		error_occurred = False
		try:
			self.__lock.acquire()

			if len(self.screenlet.ZIP) >0:
				CITY_ID = self.screenlet.ZIP #brownse to http://freemeteo.com and find your city's id_number
				print "===========================\nSelected Zip Code:", CITY_ID
				week=self.screenlet.day_translation[self.screenlet.language].copy()
				dn=datetime.date.weekday(datetime.date.today()) #current day number
				week[dn]= self.screenlet.today_translation[self.screenlet.language] #show today instead of the day name
				print "Connecting..."
				opener = urllib2.build_opener()
				opener.addheaders = [('User-agent', 'Mozilla/5.0')]
				freemeteo_7d = opener.open('http://freemeteo.com/default.asp?pid=23&gid=' + CITY_ID + '&la=' + self.screenlet.lang + '&sub_units=' + self.screenlet.unitsCode)
				html=freemeteo_7d.read()
				print "Getting current temperature..."
				#get current temperature and icon code
				freemeteo_now = opener.open('http://freemeteo.com/default.asp?pid=15&gid=' + CITY_ID + '&la=' + self.screenlet.lang + '&sub_units=' + self.screenlet.unitsCode)
				html_now=freemeteo_now.read()
				current_temp_fetch=re.search('class=temperature>([-]?\d+)',html_now)
				if current_temp_fetch!=None:
					print "OK!"
					current_temp=current_temp_fetch.group(1)
				else:
					print "FAILED!"
					current_temp=''
				print "Getting current weather icon code..."
				current_icon_code_fetch=re.search('''new\sFlashObject\('../templates/default/icons/(\d+[N|F]?).swf''',html_now) #ver 0.2: changed (\d+N?) to (\d+[N|F]?)
				if current_icon_code_fetch!=None:
					print "OK!"
					current_icon_code=current_icon_code_fetch.group(1)
				else:
					print "FAILED!"
					current_icon_code='-1'


				#Get the city's name
				print "Getting city's name..."
				getcity=re.search('''google_hints = "(.*?)\s.*?"''', html)
				fetchedCityName = getcity.group(1)
				self.screenlet.cityName = fetchedCityName		
				if self.screenlet.cityName != None:
					print "OK!"
				else:
					print "FAILED!"
			
				#Get country's Code
				print "Getting country's Code... (1st try)"
				countryCode_fetch=re.search('countryCode=([A-Z]{2})', html_now)
				if countryCode_fetch != None:
					print "OK!"
					self.screenlet.countryCode=countryCode_fetch.group(1)
				else:
					#Try one more time (needs self.cityName)
					print "Getting country's Code... (2nd try)"
					countryCode_fetch_retry=re.search(self.screenlet.cityName+',\s{1}([A-Z]{2})',html_now)
					if countryCode_fetch_retry!=None:
						print "OK!"
						self.screenlet.countryCode=countryCode_fetch_retry.group(1)
					else:
						print "FAILED!"
						self.screenlet.countryCode=''

				if self.screenlet.units=='English':
					weather_part=re.findall('''(?<=<a href="default.asp\?''' + 'sub_units=' + self.screenlet.unitsCode + '&pid=22' + '&la=' + self.screenlet.lang + '&gid=' + CITY_ID + '''&nDate=\d").*?(?=</TD>\s+</TR>)''', html, re.MULTILINE)
				else:
					weather_part=re.findall('''(?<=<a href="default.asp\?''' + 'pid=22' + '&la=' + self.screenlet.lang + '&gid=' + CITY_ID + '''&nDate=\d").*?(?=</TD>\s+</TR>)''', html, re.MULTILINE)
				weather7d={} #7days forecast (a dict per day with keys: day, description, lowtemp, hightemp, winddir, windvel, icon)

				#Current conditions
				weather7d[0]={} 
				weather7d[0]["day"]=self.screenlet.now_translation[self.screenlet.language]
				weather7d[0]["temp"]=current_temp
				weather7d[0]["icon"]=current_icon_code

				#for part in weather_part:
				#	print part
				# 7 days forecast

				print "Getting weather forecast..."
				i=0

				for part in weather_part:
					if i<4 : #Use 5 days forecast (current conditions + 4 next days)
						print part
						#setting the correct names for every next day 
						day=(dn+i>6) and week[dn+i-7] or week[dn+i] #the and-or trick
						i+=1
						weather7d[i]={}
						weather7d[i]["day"]=day
					
						#splitting day by day information
					
						#getting weather description
						info2=re.search('<TD class="tbl_stations_content">(.*?)<br>', part)
						if info2!=None:
							description=info2.group(1).replace('&nbsp;','')
							weather7d[i]["description"]=description
						else:
							weather7d[i]["description"]=''
	
						#getting high temperature
						info3=re.search(self.screenlet.temp_translation_max + ':\s([-]?\d+)', part)
						if info3!=None:
							high=info3.group(1)
							weather7d[i]["hightemp"]=high
						else:
							weather7d[i]["hightemp"]=''
	
						#getting low temperature
						info4=re.search(self.screenlet.temp_translation_min + ':\s([-]?\d+)', part)
						if info4!=None:
							low=info4.group(1)
							weather7d[i]["lowtemp"]=low
						else:
							weather7d[i]["lowtemp"]=''
	
						#getting the icon code
						icon_code=re.search('<img src="../templates/default/iconsgif/(\d+[N|F]*).gif"',part) #ver 0.2: changed (\d+N?) to (\d+[N|F]?)
						if icon_code!=None:
							code=icon_code.group(1).strip()
							weather7d[i]["icon"]=code
						else:
							weather7d[i]["icon"]='-1' #just a number that doesn't correspond to an icon code

		
				if weather7d[0]["temp"]=='':    #if no data...(TODO: find a better condition to check no data)
					print "FAILED"
					del weather7d
					weather7d={}
					if self.screenlet.show_error_message==1 and self.screenlet.updated_recently==1:
						self.screenlet.latest = weather7d
						self.screenlet.show_error()
					self.screenlet.updated_recently = 0
				else:
					print "OK!"
					self.screenlet.latest = weather7d
					self.screenlet.updated_recently = 1
			else:
				print "Please set your ZIP Code."
	
		except:
			traceback.print_exc()
			error_occurred = True
			
		finally:
			self.__lock.release()

		self.dealingWithData = False
		
		gobject.idle_add(self.screenlet.on_reloaded, not error_occurred)


@tdoc
class FreemeteoWeatherScreenlet(screenlets.Screenlet):
	"""A Minimal Weather Screenlet (powered by freemeteo.com) that uses Widescape Weather Graphics. Supports many languages."""
	
	# default meta-info for Screenlets
	__name__ = 'FreemeteoWeatherScreenlet'
	__version__ = '0.5.6++'
	__author__ = 'Nikiforakis Manos, Guido Tabbernuk'
	__category__ = 'Weather'
	__requires__ = ['python-tz']
	__desc__ = __doc__

	__timeout = None
	__notifier = None
	__updater = None

	update_interval = 300
	show_error_message = 1
	updated_recently = 0

	# editable options
	bgColor = (0.0,0.0,0.0,0.18)
	iconColor = (1,1,1,1)
	textColor = (1,1,1,1)
	roundCorner = True

	bigfont = 'Ubuntu 10'
	smallfont = 'Ubuntu 6'
	verysmallfont = 'Ubuntu 5'

	showCityTime = True
	showForecast = True
	showTrayIcon = False
	showCityTimeBackground = True
	show24HourClock = True 
	useCityTime = False 

	screenlet_width = 45
	screenlet_height = 33

	cityName = ""
	ZIP = '' 
	units = _('Metric') 
	unitsCode = '1' 

	latest = {}
	
	countryCode=''

	#Default language = English
	language='English'
	language_freemeteo='English'
	
	# translations to use getting freemeteo data
	language_sel_freemeteo = ['Bulgarian', 'Croatian', 'Czech', 'Danish', 'Dutch', 'English', 'Finnish', 'French', 'German', 'Greek', 'Hungarian', 'Italian', 'Norwegian', 'Polish', 'Portoguese', 'Romanian', 'Russian', 'Serbian', 'Spanish', 'Swedish', 'Turkish']
	languageID_freemeteo = {
			'Bulgarian':'22', 
			'Croatian':'21',
			'Czech':'12',
			'Danish':'8',
			'Dutch':'11',
			'English':'1',
			'Finnish':'10',
			'French':'6',
			'German':'3',
			'Greek':'2',
			'Hungarian':'16',
			'Italian':'13',
			'Norwegian':'9',
			'Polish':'20',
			'Portoguese':'18',
			'Romanian':'15',
			'Russian':'14',
			'Serbian':'23',
			'Spanish':'4',
			'Swedish':'5',
			'Turkish':'17'
					}
	temp_translation_freemeteo = {
			'Bulgarian':('макс.','мин.'),
			'Croatian':('Visoka','Niska'),
			'Czech':('Vys.','Nízk.'),
			'Danish':('Høj\s+','Lav\s+'), # \s+ needed for regular expression 
			'Dutch':('Hoog','Laag'),
			'English':('High','Low'),
			'Finnish':('Korkein','Alin'),
			'French':('Max','Min'),
			'German':('Max.', 'Min.'),
			'Greek':('Υψηλή', 'Χαμηλή'), 
			'Hungarian':('Max.','Min.'),
			'Italian':('Alta','Bassa'),
			'Norwegian':('Høy\s+','Lav\s+'), # \s+ needed for regular expression 
			'Polish':('Wys.','Niska'),
			'Portoguese':('Elev.','Baixa'),
			'Romanian':('Max.','Min.'),
			'Russian':('Выс.', 'Низ.'),
			'Serbian':('Maks.','Min.'),
			#'Spanish':('Máx','Mín'),
			'Spanish':('m&#225;x','m&#237;n'),
			'Swedish':('Hög','Låg'),
			'Turkish':('Yüksek','Düşük')
					}


	# translations for use inside screenlet
	language_sel = ['Bulgarian', 'Croatian', 'Czech', 'Danish', 'Dutch', 'English', 'Estonian', 'Finnish', 'French', 'German', 'Greek', 'Hungarian', 'Italian', 'Norwegian', 'Polish', 'Portoguese', 'Romanian', 'Russian', 'Serbian', 'Spanish', 'Swedish', 'Turkish']

	day_translation = {
			'Bulgarian':{0:u'Понеделник', 1:u'вторник', 2:u'сряда', 3:u'четвъртък', 4:u'петък', 5:u'събота', 6:u'неделя'},
			'Croatian':{0:u'ponedjeljak', 1:u'utorak', 2:u'srijeda', 3:u'četvrtak', 4:u'petkom', 5:u'subotu', 6:u'nedjelja'},
			'Czech':{0:u'Pondělí', 1:u'úterý', 2:u'středa', 3:u'čtvrtek', 4:u'pátek', 5:u'sobota', 6:u'neděle'},
			'Danish':{0:u'Mandag', 1:u'tirsdag', 2:u'onsdag', 3:u'torsdag', 4:u'fredag', 5:u'lørdag', 6:u'søndag'},
			'Dutch':{0:u'maandag', 1:u'dinsdag', 2:u'woensdag', 3:u'donderdag', 4:u'vrijdag', 5:u'zaterdag', 6:u'zondag'},
			'English':{0:u'Monday',1:u'Tuesday',2:u'Wednesday',3:u'Thursday',4:u'Friday',5:u'Saturday',6:u'Sunday'},
#			'Estonian':{0:u'esmaspäev', 1:u'teisipäev', 2:u'kolmapäev', 3:u'neljapäev', 4:u'reede', 5:u'laupäev', 6:u'pühapäev'},
			'Estonian':{0:u'E', 1:u'T', 2:u'K', 3:u'N', 4:u'R', 5:u'L', 6:u'P'},
			'Finnish':{0:u'Maanantai', 1:u'tiistai', 2:u'keskiviikko', 3:u'torstai', 4:u'perjantai', 5:u'lauantai', 6:u'sunnuntai'},
			'French':{0:u'lundi', 1:u'mardi', 2:u'mercredi', 3:u'jeudi', 4:u'vendredi', 5:u'samedi', 6:u'dimanche'},
			'German':{0:u'Montag', 1:u'Dienstag', 2:u'Mittwoch', 3:u'Donnerstag', 4:u'Freitag', 5:u'Samstag', 6:u'Sonntag'},
			'Greek':{0:u'Δευτέρα', 1:u'Τρίτη', 2:u'Τετάρτη', 3:u'Πέμπτη', 4:u'Παρασκευή', 5:u'Σάββατο', 6:u'Κυριακή'},
			'Hungarian':{0:u'Hétfő', 1:u'Kedd', 2:u'Szerda', 3:u'Csütörtök', 4:u'Péntek', 5:u'Szombat', 6:u'Vasárnap'},
			'Italian':{0:u'lunedì', 1:u'martedì', 2:u'mercoledì', 3:u'giovedì', 4:u'venerdì', 5:u'sabato', 6:u'domenica'},
			'Norwegian':{0:u'mandag', 1:u'tirsdag', 2:u'onsdag', 3:u'torsdag', 4:u'fredag', 5:u'lørdag', 6:u'søndag'},
			'Polish':{0:u'Poniedziałek', 1:u'wtorek', 2:u'środa', 3:u'czwartek', 4:u'piątek', 5:u'sobota', 6:u'niedziela'},
			'Portoguese':{0:u'Segunda', 1:u'terça', 2:u'quarta', 3:u'quinta', 4:u'sexta', 5:u'sábado', 6:u'domingo'},
			'Romanian':{0:u'Luni', 1:u'Marţi', 2:u'Miercuri', 3:u'Joi', 4:u'Vineri', 5:u'Sâmbătă', 6:u'duminică'},
			'Russian':{0:u'понедельник', 1:u'вторник', 2:u'среда', 3:u'четверг', 4:u'пятница', 5:u'суббота', 6:u'воскресенье'},
			'Serbian':{0:u'Понедељак', 1:u'уторак', 2:u'среда', 3:u'четвртак', 4:u'петак', 5:u'субота', 6:u'недеља'},
			'Spanish':{0:u'Lunes', 1:u'Martes', 2:u'Miércoles', 3:u'Jueves', 4:u'Viernes', 5:u'Sábado', 6:u'Domingo'},
			'Swedish':{0:u'måndag', 1:u'tisdag', 2:u'onsdag', 3:u'torsdag', 4:u'fredag', 5:u'lördag', 6:u'söndag'},
			'Turkish':{0:u'Pazartesi', 1:u'Salı', 2:u'Çarşamba', 3:u'Perşembe', 4:u'Cuma', 5:u'Cumartesi', 6:u'Pazar'}
					}

	today_translation = {
			'Bulgarian':u'Днес',
			'Croatian':u'Danas',
			'Czech':u'Dnes',
			'Danish':u'I dag',
			'Dutch':u'Vandaag',
			'English':u'Today',
			'Estonian':u'täna',
			'Finnish':u'tänään',
			'French':u'''Aujourd'hui''',
			'German':u'heute',
			'Greek':u'Σήμερα',
			'Hungarian':u'Ma',
			'Italian':u'Oggi',
			'Norwegian':u'I dag',
			'Polish':u'Dzisiaj',
			'Portoguese':u'Hoje',
			'Romanian':u'de azi',
			'Russian':u'Сегодня',
			'Serbian':u'данас',
			'Spanish':u'hoy',
			'Swedish':u'Dag',
			'Turkish':u'Bugün'
					}

	now_translation = {
			'Bulgarian':u'сега',
			'Croatian':u'sada',
			'Czech':u'teď',
			'Danish':u'nu',
			'Dutch':u'Nu',
			'English':u'Now',
			'Estonian':u'praegu',
			'Finnish':u'nyt',
			'French':u'alors',
			'German':u'jetzt',
			'Greek':u'Τώρα',
			'Hungarian':u'Most',
			'Italian':u'adesso',
			'Norwegian':u'Nå',
			'Polish':u'teraz',
			'Portoguese':u'agora',
			'Romanian':u'acum',
			'Russian':u'в настоящее',
			'Serbian':u'сада',
			'Spanish':u'ahora',
			'Swedish':u'nu',
			'Turkish':u'Üye'
					}


	# constructor
	def __init__(self, **keyword_args):
		#call super
		screenlets.Screenlet.__init__(self, height=self.screenlet_height, 
			**keyword_args)
		self.enable_buttons = False
		self.draw_buttons = False

		# set theme
		self.theme_name = "default"

		self.scale = 1.5

		# init the timeout function
		self.update_interval = self.update_interval

		# add option group
		# TODO: Hook it up to LIVE SOURCES
		# TODO: Edit Boxes entering Zipcode, Custom City Name
		#       Check Boxes for toggling Short/Expanded, City/Time display, Tray button
		#       Color selection boxes for Customizing Appearance
		# TODO: Look into Mouse Event Handling - Mouse click/over on widget -> animate open/close
		
		self.add_options_group(_('Appearance'), _('Adjust Appearance of the Widget'))
		self.add_options_group(_('Layout'), _('Adjust Layout and Behavior of the Widget'))
		self.add_options_group(_('Weather'), _('Settings for fetching Weather Information'))
		self.add_option(ColorOption(_('Appearance'), 'bgColor',
			self.bgColor, _('Background Color'),
			_('Background Color of the Widget')))
		self.add_option(ColorOption(_('Appearance'), 'iconColor',
			self.iconColor, _('Icon Color'),
			_('Color of the Weather Icons')))
		self.add_option(ColorOption(_('Appearance'), 'textColor',
			self.textColor, _('Text Color'),
			_('Color of the Text')))
		self.add_option(FontOption(_('Appearance'), 'bigfont',
			self.bigfont, _('Bigger Font'),
			_('Font used for City and current temperature')))
		self.add_option(FontOption(_('Appearance'), 'smallfont',
			self.smallfont, _('Smaller Font'),
			_('Font used for forecast temperature')))
		self.add_option(FontOption(_('Appearance'), 'verysmallfont',
			self.verysmallfont, _('Tiny Font'),
			_('Font used for forecast low temperature and dayname')))
		self.add_option(BoolOption(_('Appearance'), 'showCityTimeBackground',
			self.showCityTimeBackground, _('Show Background for City'),
			_('Show City and Time Background Color in the Widget ?')))
		self.add_option(BoolOption(_('Appearance'), 'show24HourClock',
			self.show24HourClock, _('Show 24 Hour Clock'),
			_('Show a 24 Hour Clock ?')))
		self.add_option(BoolOption(_('Appearance'), 'roundCorner',
			self.roundCorner, _('Background round corners'),_('Draw background with round corners')))
		self.add_option(BoolOption(_('Layout'), 'showCityTime',
			self.showCityTime, _('Show City and Time'),
			_('Show City and Time in the Widget ?')))
		self.add_option(BoolOption(_('Layout'), 'useCityTime',
			self.useCityTime, _("Use City's Local Time"),
			_("Use selected city's local time instead of PC's time.")))
		self.add_option(BoolOption(_('Layout'), 'showForecast',
			self.showForecast, _('Show Forecast'),
			_('Show Forecast in the Widget ?')))
		self.add_option(BoolOption(_('Layout'), 'showTrayIcon',
			self.showTrayIcon, _('Show Toggle Forecast Icon'),
			_('Show a plus/minus icon for showing or not 4-days forecast.')))
		#we should not translate the ZIP variable... 
		self.add_option(StringOption(_('Weather'), 'ZIP', 
			str(self.ZIP), _("Freemeteo's Area ZIP Code"), 
			_("Get your area's code (Zip code) from http://www.freemeteo.com :\nChoose your region and copy the number after 'gid=' part of the URL")), realtime=False)
		self.add_option(StringOption(_('Weather'), 'units', 
			self.units, _('Select units'),_('Metric=(C)elsius, English=(F)ahrenheit'),choices=[_('Metric'),_('English')]),realtime=False) 
		self.add_option(StringOption(_('Weather'), 'language', 
			self.language,_('Select language'),'',choices = self.language_sel),realtime=False)
		self.add_option(StringOption(_('Weather'), 'language_freemeteo', 
			self.language_freemeteo,_('Select language for Freemeteo.com forecasts'),'',choices = self.language_sel_freemeteo),realtime=False)
		self.add_option(BoolOption(_('Weather'), 'show_error_message', 
			bool(self.show_error_message), _('Show error messages'), 
			_('Show an error message on invalid location code')))


		#Default values
		self.updatelanguage() # Default=English
		self.updatelanguage_freemeteo() # Default=English

		self.__notifier = screenlets.utils.Notifier(self)
		self.__updater = Updater(self)

	def __setattr__(self, name, value):
		# call Screenlet.__setattr__ in baseclass (ESSENTIAL!!!!)
		screenlets.Screenlet.__setattr__(self, name, value)

		if name in ('bgColor', 'iconColor', 'textColor', 'roundCorner'):
			self.redraw_canvas()
		elif name in ('bigfont', 'smallfont', 'verysmallfont', 'showCityTime', 'showForecast', 
			'showTrayIcon', 'showCityTimeBackground', 'show24HourClock', 'useCityTime'):
			self.update_shape()
			self.redraw_canvas()

		if name == "ZIP":
			self.__dict__[name] = value
			self.update()

		if name == "update_interval":
			if value > 0:
				self.__dict__['update_interval'] = value
				if self.__timeout:
					gobject.source_remove(self.__timeout)
				self.__timeout = gobject.timeout_add(value * 1000, self.update)
			else:
				pass

		if name == 'language':
			if value == self.language :
				self.updatelanguage()
				self.update()

		if name == 'language_freemeteo':
			if value == self.language_freemeteo :
				self.updatelanguage_freemeteo()
				self.update()

		if name == 'units':
			if value==_('Metric'):
				self.unitsCode = '1'
			else:
				self.unitsCode = '2'
			self.update()

	def on_init (self):
		"""Called when the Screenlet's options have been applied and the 
		screenlet finished its initialization. If you want to have your
		Screenlet do things on startup you should use this handler."""
		
		#Menu items have been moved here...
		
		# add zip code menu item
		self.add_menuitem("zipcode", _("Zip Code..."))
		self.add_menuitem("description", _("Forecast description"))
		# add default menu items
		self.add_default_menuitems()

		if len(self.ZIP) <= 0:
			self.__notifier.notify(_("Please select desired ZIP Code to view forecast."))

	def on_draw(self, ctx):

		# if theme is loaded
		if self.theme:
			if len(self.ZIP) <= 0:
				weather = {}
				self.countryCode = ''
			else:
				weather = self.latest
			#self.window.set_keep_below(True)

			# set scale rel. to scale-attribute
			ctx.scale(self.scale, self.scale)

			if weather == {}:
				self.cityName = ""

			maincellx = 0
			citytimewidth = 0
			maincellwidth = 48
			citywidth = 0
			timewidth = 0
			cityheight = 0

			if self.useCityTime:
				try: #version 0.2
					import pytz
					if self.countryCode=='':
						print "Country code not provided, using PC's time..."
						tm=time
					else:
						print 'Using local timezone: %s' %self.countryCode
						tzname = pytz.country_timezones(self.countryCode)[0]
						tz = pytz.timezone(tzname)
						tm = datetime.datetime.now(tz)
				except:
					print "Pytz python module not found, reverting to PC's time"
					# create dialog
#					dialog = gtk.Dialog("Python Timezone module not installed!", self.window)
#					dialog.resize(300, 100)
#					dialog.add_buttons(gtk.STOCK_OK, gtk.RESPONSE_OK)
#					text="Python timezone module (pytz) is needed for local time.\nUbuntu users please install python-tz.\nReverting to PC's time"
#					label = gtk.Label(text)
#					dialog.vbox.add(label)
#					dialog.show_all()
#					response = dialog.run()
#					if response == gtk.RESPONSE_OK:
					self.useCityTime = False
#					dialog.hide()
					#Reverting to PC's time
					tm=time
			else: #Using Pc's time
				tm=time

			curtime = ""
			if self.show24HourClock:
				curtime = tm.strftime("%H:%M")
			else:
				curtime = tm.strftime("%l:%M %P")


			if self.showCityTime:
				cx, cy, citywidth, cityheight = self.get_text_extents(ctx, self.cityName, self.bigfont);
				timewidth = self.get_text_width(ctx, curtime, self.smallfont)
				if citywidth > timewidth: citytimewidth = citywidth + 6
				else: citytimewidth = timewidth + 6
				maincellwidth += citytimewidth 

			self.screenlet_width = maincellwidth

			if not self.showCityTimeBackground:
				maincellx = citytimewidth

			self.draw_background(ctx, maincellx, maincellwidth, self.showForecast)

			if self.showCityTime and len(self.cityName) > 0:
				self.draw_text(ctx, self.cityName, citytimewidth-citywidth-3, 1, self.bigfont, self.textColor)
				self.draw_text(ctx, "@ " + curtime, citytimewidth-timewidth-4, cityheight + 7, self.verysmallfont, self.textColor)

			# show Current and Today/Tonight's data
			if weather != {}:
				self.draw_weather_icon(ctx, self.get_icon(weather[0]["icon"]), weather[0]["day"], weather[0]["temp"],'', maincellwidth, 1)
			else:
				if len(self.ZIP) <= 0:
					self.draw_text(ctx, _("Please set your ZIP Code... "), 4, 4, self.verysmallfont, self.textColor)
				else:
	#				self.draw_text(ctx, self.cityName, citytimewidth-citywidth-3, 1, self.bigfont, self.textColor)
					self.draw_text(ctx, _("Connecting... "), 4, 4, self.verysmallfont, self.textColor)
	#				self.draw_weather_icon(ctx, "waiting", '', '','', maincellwidth, 1)


			if self.showForecast:
				self.screenlet_width += 180

				if len(weather) > 0:
					for x in range(1,min(5, len(weather))):
						if weather[x]["hightemp"]=='':
							weather[x]["hightemp"]=weather[x]["lowtemp"] #to show the only available temperature on top with bigfont!
							weather[x]["lowtemp"]=''
						day = weather[x]["day"]
						self.draw_weather_icon(ctx, self.get_icon(weather[x]["icon"]), 
							day, weather[x]["hightemp"], weather[x]["lowtemp"], maincellwidth, x+1)
				else:
#					self.draw_scaled_colorized_pixmap(ctx,'waiting.png', maincellwidth , 0, 44, 33, self.iconColor)
#					self.draw_scaled_colorized_pixmap(ctx,'freemeteo.png', maincellwidth , -8, 167, 36, self.iconColor)
					self.draw_scaled_colorized_pixmap(ctx,'freemeteo.png', 16 , 6, 100, 21, self.iconColor)
#					self.draw_colorized_pixmap(ctx,'freemeteo.png', maincellwidth , 0, self.iconColor)
#					self.draw_pixmap(ctx,'freemeteo.png', maincellwidth , 0, self.iconColor)

			if self.width != self.screenlet_width:
				self.width = self.screenlet_width




	def on_draw_shape(self, ctx):
		#self.on_draw(ctx)
#		print self.screenlet_width
#		print self.screenlet_height
		ctx.scale(self.scale, self.scale)
		ctx.set_source_rgba(1,1,1,1)
		ctx.rectangle(0,0,self.screenlet_width,self.screenlet_height)
		ctx.paint()

	def on_mouse_down(self, event):
		if event.type == gtk.gdk._2BUTTON_PRESS: 
			self.showForecast = not self.showForecast
			if self.window:
				self.redraw_canvas()
				return True
		return False
	
	def draw_weather_icon(self, ctx, iconname, dayname, hightemp, lowtemp, w, index):
		# Draw the weather icon
		self.draw_scaled_colorized_pixmap(ctx,iconname+'.png', w + 45*(index-2), 0, 44, 33, self.iconColor)
		# Display the Day
		if dayname != "":
			#self.draw_scaled_colorized_pixmap(ctx,'Day-'+dayname+'.png', w + 45*(index-2), 24, 28, 8, self.textColor) #using images
			if dayname in (self.today_translation[self.language], self.now_translation[self.language]):
				self.draw_text(ctx, dayname, w + 45*(index-2)+5, 26, self.verysmallfont, self.textColor)
			else:
				#width = self.get_text_width(ctx, dayname[:3], self.verysmallfont)
				self.draw_text(ctx, dayname[:3], w + 45*(index-2)+5, 26, self.verysmallfont, self.textColor)

		# Display the Temperature
		if hightemp != "": 
			hightemp = hightemp+u"° "
			if index == 1:
				width = self.get_text_width(ctx, hightemp, self.bigfont)
				self.draw_text(ctx, hightemp, w + 45*(index-1)-22-width, 1, self.bigfont, self.textColor)
			else:
				width = self.get_text_width(ctx, hightemp, self.smallfont)
				self.draw_text(ctx, hightemp, w + 45*(index-1)-22-width, 2, self.smallfont, self.textColor)
		if lowtemp != "": 
			lowtemp = lowtemp+u"° "
			if index == 1:
				width = self.get_text_width(ctx, lowtemp, self.smallfont)
				self.draw_text(ctx, lowtemp, w + 45*(index-2)+5, 13, self.smallfont, self.textColor)
			else:
				width = self.get_text_width(ctx, lowtemp, self.verysmallfont)
				self.draw_text(ctx, lowtemp, w + 45*(index-2)+5, 14, self.verysmallfont, self.textColor)



	def draw_background(self, ctx, x, w, isOpen):

		if isOpen:
			add = 180
		else:
			add = 0

		# draw the normal background
#		ctx.set_source_rgba(self.bg_rgba_color[0], self.bg_rgba_color[1], self.bg_rgba_color[2], self.bg_rgba_color[3])
		ctx.set_source_rgba(self.bgColor[0],self.bgColor[1],self.bgColor[2],self.bgColor[3]) 
		if self.roundCorner:
			self.draw_rounded_rectangle(ctx,x,0, 33/15*self.scale,w+add, 33)
		else:
			self.draw_rectangle(ctx,x,0, w+add, 33)


		# draw Tray Open/Close Button
		if self.showTrayIcon:
			self.draw_tray_button(ctx, w, isOpen)

	def draw_tray_button(self, ctx, w, isOpen):
		status = "closed"
		if isOpen: status = "open"
		self.draw_scaled_colorized_pixmap(ctx,'trayButton-'+status+'.png', w - 10, 22, 9, 9, self.iconColor)
	
	def draw_colorized_pixmap(self, ctx, pixmap, x, y, color):
		#ctx.move_to(x,y);
		#ctx.set_source_surface(self.theme[pixmap], 0, 0)
		#ctx.paint()
		ctx.move_to(x,y)
		ctx.set_source_rgba(color[0], color[1], color[2], color[3])
		ctx.mask_surface(self.theme[pixmap], 0, 0)
		ctx.stroke()

	def draw_scaled_colorized_pixmap(self, ctx, pixmap, x, y, w, h, color):
		# Scale the pixmap

#		print pixmap
#		print self.theme
#		print self.theme[pixmap]
		iw = float(self.theme[pixmap].get_width())
		ih = float(self.theme[pixmap].get_height())
		matrix = cairo.Matrix(xx=iw/w, yy=ih/h)
		matrix.translate(-x, -y)
		pattern = cairo.SurfacePattern(self.theme[pixmap])
		pattern.set_matrix(matrix)
		# Make the pixmap a mask
		ctx.move_to(x,y)
		ctx.set_source_rgba(color[0], color[1], color[2], color[3])
		ctx.mask(pattern)
		ctx.stroke()
	
	def get_text_width(self, ctx, text, font):
		ctx.move_to(0,0)
		p_layout = ctx.create_layout()
		p_fdesc = pango.FontDescription(font)
		p_layout.set_font_description(p_fdesc)
		p_layout.set_text(text)
		extents, lextents = p_layout.get_pixel_extents()
		return extents[2]

	def get_text_extents(self, ctx, text, font):
		ctx.move_to(0,0)
		p_layout = ctx.create_layout()
		p_fdesc = pango.FontDescription(font)
		p_layout.set_font_description(p_fdesc)
		p_layout.set_text(text)
		extents, lextents = p_layout.get_pixel_extents()
		return extents

	def draw_text(self, ctx, text, x, y, font, color):
		p_layout = ctx.create_layout()
		p_fdesc = pango.FontDescription(font)
		p_layout.set_font_description(p_fdesc)
		p_layout.set_text(text)
		extents, lextents = p_layout.get_pixel_extents()

		ctx.move_to(x,y)
		ctx.set_source_rgba(color[0], color[1], color[2], color[3])
		ctx.show_layout(p_layout)

	def on_reloaded (self, result):
		"""Called by updater"""
		self.window.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.LEFT_PTR))	

		if result == True:
			self.redraw_canvas()


	def update(self):
		self.window.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))
		self.__updater.run()

		return True

	def get_icon(self, code): 
		#Thunderstorms
		if code in ('9', '10', '11', '16', '17', '22', '23', '28', '29'):
			weather = "thunderstorms"
		elif code in ('34', '39', '44', '49'):
			weather = "sunnythunderstorm"
		#Rain
		elif code in ('40', '18', '19', '20', '21', '33'):
			weather = "sleet"
		elif code in ('41', '42', '43', '15', '38'):
			weather = "icyrain"
		elif code in ('7','14'):
			weather = "showers"
		elif code in ('30', '31', '32', '33'):
			weather = "sunnyshowers"
		elif code in ('6', '7'):
			weather = "drizzle" 
		elif code in ('5', '12', '35', '36', '37', '13'):
			weather = "icydrizzle"
		elif code in ('33', '8'):
			weather = "rain"
		#Snow
		elif code in ('27', '48'):
			weather = "normalsnow"
		elif code in ('24', '25', '46'):
			weather = "lightsnowflurries"
		elif code in ('45', '26', '47'):
			weather = "medsnow"
		#Usual
		elif code == '4':
			weather = "cloudy"
		elif code == '3':
			weather = "mostlycloudyday"
		elif code == '2':
			weather = "partiallycloudyday"
		elif code == '1':
			weather = "clearday"
		elif code == '44':
			weather = "partiallycloudyday"
		#Night
		elif code == '3N':
			weather = "mostlycloudynight"
		elif code == '2N':
			weather = "partiallycloudynight"
		elif code == '1N':
			weather = "clearnight"
		elif code in ('30N', '31N','32N','33N', '34N', '35N', '36N', '37N', '38N', '39N', '40N', '41N', '44N', '49N'):
 			weather = "nightrain"
		elif code in ('42N', '43N', '45N', '46N', '47N', '48N'):
 			weather = "nightsnow"
 		#Foggy -added in version 0.2
 		elif code in ('1F', '2F', '3F', '4F', '1NF', '2NF', '3NF'): #NF = Night Fog ADDED in 0.2.1
 			weather = "fog"
		#the following are foggy conditions that we have no icon for...
		elif code == '7F':
			weather = "showers"
		elif code in ('10F', '28F'):
			weather = "thunderstorms"
		elif code == '26F':
			weather = "medsnow"
		#Everything else...
		else:
			weather = "unknown"

		return weather

		
	def menuitem_callback(self, widget, id):
		screenlets.Screenlet.menuitem_callback(self, widget, id)
		if id=="zipcode":
			self.show_edit_dialog()
		elif id=="description":
			self.show_info_dialog()

	def show_edit_dialog(self):
		# create dialog
		dialog = gtk.Dialog(_("Zip Code"), self.window)
		dialog.resize(300, 100)
		dialog.add_buttons(gtk.STOCK_OK, gtk.RESPONSE_OK, 
			gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
		entrybox = gtk.Entry()
		entrybox.set_text(str(self.ZIP))
		text=_("Get your area's code (Zip code) from http://www.freemeteo.com :\nChoose your region and copy the number after 'gid=' part of the URL")
		label = gtk.Label(text)
		dialog.vbox.add(label)
		dialog.vbox.add(entrybox)
		#entrybox.show()	
		dialog.show_all()
		# run dialog
		response = dialog.run()
		if response == gtk.RESPONSE_OK:
			self.ZIP = entrybox.get_text()
			self.updated_recently = 1
		dialog.hide()



	def show_info_dialog(self):
		# create dialog
		dialog = gtk.Dialog(_("Forecast description"), self.window)
		dialog.resize(300, 100)
		dialog.add_buttons(gtk.STOCK_OK, gtk.RESPONSE_OK)
		try:
			d=[]
			for i in range(1,5):
				d.append(self.latest[i]["day"] + ': ' + self.latest[i]["description"])
			text='\n'.join(d)
		except KeyError:
			text=_('There was an error fetching freemeteo servers. Please try again later...')
		finally:
			label = gtk.Label(text)
			dialog.vbox.add(label)
			dialog.show_all()
			response = dialog.run()
			if response == gtk.RESPONSE_OK:
				dialog.hide()

	def updatelanguage_freemeteo(self):
		self.lang = self.languageID_freemeteo[self.language_freemeteo] # Default=English		
		self.temp_translation_max = self.temp_translation_freemeteo[self.language_freemeteo][0] # Default=English
		self.temp_translation_min = self.temp_translation_freemeteo[self.language_freemeteo][1] # Default=English


	def updatelanguage(self):
		return

	def show_error(self):
		self.__notifier.notify(_("Could not reach Freemeteo.com. Check your internet connection and location and try again."))

# If the program is run directly or passed as an argument to the python
# interpreter then create a Screenlet instance and show it
if __name__ == "__main__":
	import screenlets.session
	screenlets.session.create_session(FreemeteoWeatherScreenlet, threading=True)
#	screenlets.session.create_session(FreemeteoWeatherScreenlet)
