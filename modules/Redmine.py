from redminelib import Redmine
from pytz import timezone
import pytz
import datetime
from datetime import timedelta 
from subprocess import Popen,PIPE
import subprocess

from Messengers import Telegram

#Linux
#sudo pip3 install python-redmine
#sudo pip3 install pytz

#Настройки
REDMINE_URL = 'http://localhost:3000/'
REDMINE_KEY = 'ae051b4e215b97d14b923688537582cf4f2008e8'
TIME_ZONE = 'Europe/Minsk'
TIMEOUT = 10
#username='vector', password='MortraLock214'

#Будет опрелелена во время выполнения
PRODUCTION_LOG_DIR = ""

#Настройка объекта Redmine
redmine = Redmine(REDMINE_URL, key=REDMINE_KEY, version='3.4.0', requests={'verify': False})
userListForSendingMessage = []

def redmineActivity():
    #print("Активность Redmine\n")

    #Получение всех пользователй с Redmine
    users = list(redmine.user.all())

    findArgs = ["find","/home/vector/redmine-3.4/log", "-name", "production.log"]

    process = subprocess.run(findArgs, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8')

    #Количество найденных файлов
    fileList = process.stdout.split("\n")

    if(len(fileList)-1 == 1):
        #print("Файл prodution.log найден:\n" + process.stdout)

        global PRODUCTION_LOG_DIR 
        PRODUCTION_LOG_DIR = fileList[0]

        #Аргументы для создания команды
        serchByUsernameArgs = ["grep", "-b", "-B5", "Current user: admin", PRODUCTION_LOG_DIR]
        findLastActivity = ["grep", "Started GET"]
        sortOutputArgs = ["sort", "-n", "-r"]
        findLastArg = ["grep", "Started GET", "--max-count=1"]

        for user in users:

            serchByUsernameArgs[3] = "Current user: " + user.login
            
            try:
                #Время последней авторизации UTC
                dt_utc = datetime.datetime(user.last_login_on.year, user.last_login_on.month, user.last_login_on.day,user.last_login_on.hour,user.last_login_on.minute, user.last_login_on.second,0,tzinfo=pytz.UTC)

                #Время последней авторизации Local Time
                dt_mtn = dt_utc.astimezone(pytz.timezone(TIME_ZONE))

            except AttributeError:
                #print("Пользователь: " + user.login + " еще не авторизовался ни разу\n")
                continue
           
            #Выполнение команд
            p1 = Popen(serchByUsernameArgs, stdout=PIPE)
            p2 = Popen(findLastActivity, stdin=p1.stdout, stdout=PIPE)
            p3 = Popen(sortOutputArgs, stdin=p2.stdout, stdout=PIPE)
            p4 = Popen(findLastArg, stdin=p3.stdout, stdout=PIPE)

            output = p4.communicate()[0]
            
            lastActivityDate = lastActivityStringFormat(output)

            if checkDateActivity(lastActivityDate) == False:
                #print("Пользователь: " + user.login + " не проявлял сегодня активность\n")
                continue

            checkTimeTracker(user.login, lastActivityDate)    
            

            #print("Пользователь: " + user.login)
            #print("Авторизация: " + dt_mtn.strftime('%Y/%m/%d %H:%M:%S'))
            #print("Активность: " + str(lastActivityDate) +"\n")

        #---------------------------------------------------------------------------
        p1.stdout.close()
        p2.stdout.close()
        p3.stdout.close()
        p4.stdout.close()

        sendMessage()

    elif(len(fileList)-1 > 1):
        print("Ошибка: найдено больше одного файла")
    else:
        print("Ошибка: файл не найден")


#Метод достает дату из строки активности пользователя
def lastActivityStringFormat(output):

    activityString = output.decode("utf-8").split(" ")
    lastActivityDate = datetime.datetime.strptime(activityString[6] + " " + activityString[7],"%Y-%m-%d %H:%M:%S")
    return lastActivityDate

#Проверка последней даты активности
def checkDateActivity(date):

    lastActivitiDate = datetime.datetime.date(date)
    todayDate = datetime.date.today()

    if lastActivitiDate < todayDate:
        return False
    else:
        return True

#Проверка последней активности time_tracker
def checkTimeTracker(username, lastActivityDate):

    lastTimeTrackerStart = findLastTimeTrackerStartOrStop("start", username)
    if not lastTimeTrackerStart:
        userListForSendingMessage.append(username)
        #print("Пользователь: " + username + " ни разу не запускал таймер\n")
        return

    lastTimeTrackerStop = findLastTimeTrackerStartOrStop("stop", username)
    if not lastTimeTrackerStop:
        #print("Пользователь: " + username + " ни разу не останавливал таймер\n")
        return

    lastTimeTrackerStartFormatted = lastActivityStringFormat(lastTimeTrackerStart)
    lastTimeTrackerStopFormatted = lastActivityStringFormat(lastTimeTrackerStop)

    #print("start: " + str(lastTimeTrackerStartFormatted))
    #print("stop: " + str(lastTimeTrackerStopFormatted))

    #if datetime.datetime.date(lastTimeTrackerStartFormatted) < datetime.date.today():
        #userListForSendingMessage.append(username)
        #return

    #Таймер включен и есть активость 
    if lastTimeTrackerStopFormatted < lastTimeTrackerStartFormatted:
        return 0
    #Таймер выключен и есть активность
    elif (lastTimeTrackerStopFormatted > lastTimeTrackerStartFormatted) and (lastActivityDate > (lastTimeTrackerStopFormatted + timedelta(minutes=TIMEOUT))):
        userListForSendingMessage.append(username) #sendMessage(username)
        return

#Поиск последнего запуска и остановки таймера в production.log файле
def findLastTimeTrackerStartOrStop(arg, username):

    #Аргументы для создания команды
    serchByUsernameArgs = ["grep", "-b", "-B3", "Current user: " + username, PRODUCTION_LOG_DIR]
    findLastTimeTreckerActivity = ["grep","-B2", "Processing by Hourglass::TimeTrackersController#" + arg]
    sortOutputArgs = ["sort", "-n", "-r"]
    findLastArg = ["grep", "Started POST", "--max-count=1"]

    if arg == "stop":
        findLastArg[1] = "Started DELETE"
    
    #Выполнение команд
    p1 = Popen(serchByUsernameArgs, stdout=PIPE)
    p2 = Popen(findLastTimeTreckerActivity, stdin=p1.stdout, stdout=PIPE)
    p3 = Popen(sortOutputArgs, stdin=p2.stdout, stdout=PIPE)
    p4 = Popen(findLastArg, stdin=p3.stdout, stdout=PIPE)

    output = p4.communicate()[0]
    
    p1.stdout.close()
    p2.stdout.close()
    p3.stdout.close()
    p4.stdout.close()

    return output

#Отправка сообщения пользователю
def sendMessage():

    if len(userListForSendingMessage) == 0:
        return

    message = "Активность Redmine\nПользователи у которых отключен таймер:\n\n"

    i = 0
    for username in userListForSendingMessage:
        i += 1
        message += str(i) + ". " + username + "\n"

    Telegram.sendMessage(message)
    #print("Пользователю " + user + " отправлено сообщение запустить таймер")
