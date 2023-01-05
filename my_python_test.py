import appdaemon.plugins.hass.hassapi as hass
import tibber
import sys
import datetime as dt
import time
import numpy as np

#print('Number of arguments:', len(sys.argv), 'arguments.')
#print('Argument List:', str(sys.argv))

class ElectricityPrice(hass.Hass):

  def initialize(self):
    self.log("Initializing ElectricityPrice")
    self.listen_state(self.getChargeThreshold, "input_button.paborja_laddning")
    self.account = tibber.Account("TOKEN") # Log in with an access token. All information gets updated here and stored in cache.
    # These properties are retrieved from cache
    self.log(self.account.name)
    self.log(self.account.user_id)
    self.log(self.account.account_type)
    self.log(self.account.login)

    self.home = self.account.homes[0]
    self.mySubscription = self.home.current_subscription


  def getChargeThreshold(self, entity, attribute, old, new, kwargs):
    self.log("getChargeThreshold")
    #self.account.update()
    PrisInfo = self.mySubscription.price_info
    ElprisNu = PrisInfo.current
    ElprisIdag = PrisInfo.today
    ElprisImorgon = PrisInfo.tomorrow
    arrayOfElpris = np.array([9.99] * 48)
    
    #Calculate how many full hours we need to charge given chanrge effect of 2kW and 64kWh battery
    ProcentAttLadda = float(self.get_state("input_number.procent_att_ladda"))
    self.log("ProcentAttLadda: %f", ProcentAttLadda)
    kWhAttLadda = ProcentAttLadda*64/100
    TimmarAttLadda = int(round(kWhAttLadda/2,0))
    self.log("TimmarAttLadda: %i", TimmarAttLadda)
    
    #In how many hours do we need to be ready 
    nowTime = float(time.time())
    timeToBeReady = float(self.get_state("input_datetime.laddning_avslutad", attribute="timestamp"))
    hoursUntilToBeReady = int((timeToBeReady - nowTime)/3600)
    #self.log("endTime: %f", endTime)
    #self.log("nowTime: %f", nowTime)
    self.log("We need to be ready within %i hour", hoursUntilToBeReady)
   
    #Get the hourly prices for today, staring at curren hour
    nowHour= int(dt.datetime.today().hour)
    self.log("nowHour: %i", nowHour)

    self.log("Nuvarande elpris: %f %f ", ElprisNu.total, ElprisIdag[nowHour].total)

    arrayPos = 0
    for i in range (nowHour, 24):
        #self.log(ElprisIdag[i].total)
        arrayOfElpris[arrayPos] = ElprisIdag[i].total
        arrayPos = arrayPos + 1
    
    #If available get the hourly proces for tomorrow as well.
    self.log("Number of hours received for tomorrow: %i", len(ElprisImorgon))
    if len(ElprisImorgon) > 0:
        for hour in ElprisImorgon:
            #self.log(hour.total)
            arrayOfElpris[arrayPos] = hour.total
            arrayPos = arrayPos + 1
    else:
        self.log("Inget pris för morgondagten tillgänligt än")
        
    #Scrap hourly proces beyond the time when we want to be ready
    for i in range (hoursUntilToBeReady, 48):
        arrayOfElpris[i] = 9.99
    
    #Sort the list of hourly prices and...    
    sortedArrayOfElpris = np.sort(arrayOfElpris)
    for i in sortedArrayOfElpris:
        self.log(i)
    #...get the threshold on whether to charge or not.
    chargeThreshold = sortedArrayOfElpris[TimmarAttLadda]
    self.log("chargeThreshold: %f", chargeThreshold)
        
    self.set_value("input_number.smartchargethreashold", int(chargeThreshold*100))
    
    #Start chanrging
    self.turn_on("input_boolean.laddboxenable")
    
    #Register callback in timeToBeReady hours
    self.log("Stop charning at %s", dt.datetime.fromtimestamp(timeToBeReady))
    handle = self.run_at(self.stopCharging, dt.datetime.fromtimestamp(timeToBeReady))
    self.log("Return from self.run_at function %s", handle)
    
    
  def stopCharging(self, kwargs):
      self.log("stopCharging")
      self.turn_off("input_boolean.laddboxenable")

  def terminate(self):
      self.log("Terminating EletricityPrice")
        