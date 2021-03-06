#!/usr/bin/python
import sys,cv2,os,time,datetime,pickle,subprocess,json,urllib2,requests,httplib2
from random import randint

types=['jpg','jpeg','JPG','JPEG']
url="http://localhost:5000"
xset=os.path.exists("/usr/bin/xset")
tvservice=os.path.exists("/usr/bin/tvservice")
LogFile="/opt/frame/log/show.log"
HistoryFile="/opt/frame/www/history.html"

class show:
  def __init__(self):
    self.write_log("------------")
    self.write_log("* Starting *")
    self.tvservice_on()
    self.update_rest("/config/10", {"id":'10', "key":'reread', "value": 'true' } )
    self.import_config()
    self.write_log("* finish importing config *")
    self.import_config_state()
    self.List=[]
    self.Shown=[]
    for path, subdirs, files in os.walk(self.root):
      self.write_log(str(path))
      for name in files:
        self.List.append(unicode(path)+"/"+unicode(name))

    self.write_log("Total of "+str(len(self.List))+" images in "+str(self.root))
    self.List.sort()
    self.main()

  def tvservice_on(self):
     os.system('service xserver start')
     if tvservice:
        print "Tvservice on"
        os.system('/usr/bin/tvservice -p')  

  def stop_loading_service(self):
    os.system('service loading stop')  

  def import_config_state(self):
    self.yscreenresulation=int(requests.get(url+"/config/4").json()["value"])
    self.xscreenresulation=int(requests.get(url+"/config/3").json()["value"])

  def check_import_config(self):
    reread=requests.get(url+"/config/10").json()["value"]
    if reread=="true":
        print "Importig config"
        self.import_config
        self.update_rest("/config/10", {"id":'10', "key":'reread', "value": 'false' } )
        return (1)

  def import_config(self):
    self.root=requests.get(url+"/config/1").json()["value"]
    self.delay=int(requests.get(url+"/config/2").json()["value"])
    self.series=requests.get(url+"/config/5").json()["value"]
    self.grayscale=requests.get(url+"/config/6").json()["value"]
    self.show_half=requests.get(url+"/config/7").json()["value"]
    #self.check_net=(requests.get(url+"/config/8").json()["value"])
    self.check_net=0
    
  def get_hours_on(self):
    now=datetime.datetime.now()
    hours=(requests.get(url+"/days/"+self.day).json()["hours"][now.hour])
    return hours 
  
  def get_hours_show(self):
    now=datetime.datetime.now()
    hours=(requests.get(url+"/h_display/"+self.day).json()["hours"][now.hour])
    return hours

  def xset_force_on(self):
    if xset:
      os.system('export DISPLAY=:0; /usr/bin/xset dpms force on')  

  def read_img(self):
    self.img=cv2.imread(self.FileName)
    print self.FileName
    self.write_log(self.FileName+" "+str(self.img.shape))  
    self.write_history_html(self.FileName)
    if self.grayscale=="true": 
      self.img=cv2.cvtColor(self.img, cv2.COLOR_BGR2GRAY)

  def show(self):
    self.update_image_name()
    cv2.namedWindow("Frame", cv2.WINDOW_AUTOSIZE )
    r = int(long(self.yscreenresulation*1000 / self.img.shape[0]*1000)) # *1000 cause we need better precision
    dim = (int(self.img.shape[1]*r)/1000000,self.yscreenresulation)
    self.img=cv2.resize(self.img, dim, interpolation = cv2.INTER_AREA)
    cv2.moveWindow("Frame", int((self.xscreenresulation-self.img.shape[1])/2), 0) 
    cv2.imshow("Frame",self.img)
    time.sleep(1)
    f=0
    while ( f < int(self.delay/10) ):
      f+=1
      self.xset_force_on()
      key=cv2.waitKey(10000)
      check=self.check_import_config()
      if check==1:
        break

  def update_rest(self,lurl,data):
    etag=requests.get(url+lurl).json()["_etag"]
    headers = {'If-Match': etag,'content-type': 'application/json', 'Accept-Charset': 'UTF-8'}
    r = requests.patch(url+lurl, data=json.dumps(data), headers=headers)

  def update_image_name(self): # export image name to Eve
    imagename = '{"image_name": "'+str(self.FileName)+'"}'
    self.update_rest("/state/1", imagename )

  def add_hour(self):  # Adding hour to displayed image
    hours_show=self.get_hours_show()
    if hours_show=="1":
      self.msg=time.strftime("%H:%M")
      self.add_text()
      return

    if self.show_half=="1" and (time.strftime("%M")=='30' or time.strftime("%M")=='00'):
       self.msg=time.strftime("%H:%M")
       self.add_text()
  
  def check_net(self): #Check internet connection
    Status=subprocess.Popen("/bin/ping -c1 -w2 " +str (Net_target), shell=True, stdout=subprocess.PIPE).stdout.read()
    if Status.find ('100% packet loss') > 0:
      self.msg=":( "+self.msg
      self.add_text()

  def add_text(self,x=50,y=170,scale=1):
    font=cv2.FONT_HERSHEY_SIMPLEX
#    size=scale*((self.img.shape[1::-1])[1]/300+((self.img.shape[1::-1])[0]))/400
    size=3
    y=((self.img.shape[1::-1])[1])/7
    x=((self.img.shape[1::-1])[0])/40
    cv2.putText(self.img, self.msg, (x,y), font, size,(0,0,0),17)
    cv2.putText(self.img, self.msg, (x,y), font, size,(255,255,255),7)

  def check_on_off(self):
    hours_on=self.get_hours_on()
    if hours_on=="1":
      self.xset_force_on()
      return 1
    else:
      print hours_on
      self.write_log("Killing my self") 
      os.system('service frame start')  
      os.system('service show stop')  
      sys.exit(0)

  def write_log(self,Text):
    print(time.strftime("%H:%M:%S ")+Text+"\n")
    f=open(LogFile,'a')
    f.write(time.strftime("%H:%M:%S ")+Text+"\n")
    f.close()

  def write_history_html(self,Text):
    FileName=Text.replace("/home/","")
    History=[]
    History.append(str(time.strftime("<p>%H:%M:%S ")+"<a href="+FileName+" download link>"+FileName+"</a></font></center></p>\n"))
    try:
      with open(HistoryFile) as f:
        for g in range(0,100):
         Line=f.readline()
         if len(Line)>1:
           History.append(str(Line))
      f.close()
    except:
      print "Starting new file"

    f=open(HistoryFile,'w') 
    for g in range(0,len(History)):
      f.write(str(History[g]))
    f.close()

  def display(self):
    self.msg=""
    self.Hour=str(time.strftime("%H"))
    self.day=int(datetime.datetime.today().weekday()+2)
    if self.day > 7:
      self.day=self.day-7
    self.day=str(self.day)
    if self.check_net != 0:
      self.check_net()
    if self.check_on_off():
      self.read_img()
      self.add_hour()
      self.show()

  def main(self):
    count=0
    if (len(self.List))<int(self.series):
      f=1
    else:
      f=randint(0,(len(self.List)-int(self.series)))

    self.stop_loading_service()
    while 1:
      self.FileName=self.List[f]
      self.display()
      count+=1
      f+=1
      if count>=self.series:
        count=0
        f=randint(0,len(self.List)-self.series)

os.environ['DISPLAY']=':0'        
show01 = show()


