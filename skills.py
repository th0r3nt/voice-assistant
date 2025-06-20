import os #взаимодействие с операционной системой.
import webbrowser #взаимодействие с браузером.
import random # этот модуль нужен для "оживления" ответов ассистента.
import config #импортируем соседний файл как модуль.
import datetime
import requests
import locale
from pydub import AudioSegment #Теперь в функции open_notepad вы можете использовать более короткий вызов без (название функции).(название функции)(фраза).
from pydub.playback import play
import psutil
from fuzzywuzzy import process
import api_keys

AudioSegment.converter = r"C:\Users\ivanc\voice-assistant\NEED\ffmpeg.exe"

MONTHS = (
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря"
)


def play_sound (engine, sound_list, fallback_phrase="Выполнено, Сэр."):
    try:
        sound_path = random.choice(sound_list)
        audio_segment = AudioSegment.from_mp3(sound_path)
        play(audio_segment)
    except Exception as error: #Если что-то пошло не так (файл не найден, неверный формат и т.д.).
        print(f"Ошибка воспроизведения звука: {error}")
        # ...тогда произносим голосом запасную фразу.
        engine.say(fallback_phrase)
        engine.runAndWait()

def launch_app(engine, task_name):
    words = task_name.split() #разбиваем команду на слова, "открой блокнот" превратится в ['открой', 'блокнот'].

    if len(words) > 1: #len(words) считает количество слов в списке: проверяем, есть ли в команде что-то, кроме одного слова-триггера.
    #Если слов больше одного, значит, команда полная. Мы заходим внутрь блока if.
    #Если слово только одно, значит, команда неполная. Мы пропускаем if и попадаем в блок else.

        app_name_human = " ".join(words[1:]) #берем все, что идет после первого слова.

        executable_name = config.APP_ALIASES.get(app_name_human.lower(), app_name_human + ".exe") #используем наш словарь-переводчик, как и раньше
        #памятка: .lower преобразует все символы в строке в нижний регистр.

        play_sound(engine, config.SOUNDS_OF_REQUEST, f"Запускаю {app_name_human}, Сэр.")

        try:
            os.startfile(executable_name)
        except FileNotFoundError:
            engine.say(f"Не могу найти программу {executable_name}, Сэр.")
            engine.runAndWait()

        return None
    
    else:
        return "уточнить_запуск"

def close_app(engine, task_name):
    words = task_name.split()

    if len(words) > 1: #сценарий 1: Команда полная (например, "закрой блокнот").
        app_name_to_close = " ".join(words[1:])
        executable_to_close = config.APP_ALIASES.get(app_name_to_close.lower(), app_name_to_close + ".exe")
        process_found = False

        #Аргумент ['pid', 'name'] — это инструкция: "Для каждой программы, которую ты встретишь, доложи мне две вещи: 
        #ее уникальный номер (pid - Process ID) и ее системное имя (name)".

        for proc in psutil.process_iter(['pid', 'name']): # Код for proc in psutil.process_iter(...) — это процесс патрулирования. 
            #На каждом шаге цикла переменная proc становится объектом, который представляет одну конкретную запущенную программу (Блокнот, Chrome, Steam и т.д.).

            #proc.info['name'] — это как спросить: "Какое имя у той программы, которую ты сейчас сканируешь?".
            if proc.info['name'].lower() == executable_to_close.lower(): #Аналогия: Операция по нейтрализации цели.
                #if proc.info['name']... - патрульный докладывает: "Я нашел цель! Процесс с именем notepad.exe обнаружен!".

                try: #Мы начинаем операцию по нейтрализации. Это наш "оптимистичный" сценарий.
                    program = psutil.Process(proc.info['pid']) #мы говорим нашему "снайперу": "Вот уникальный номер цели. Приготовься к выстрелу".
                    program.terminate() #команда "Огонь!". Мы отправляем процессу сигнал на завершение.
                    process_found = True
                    play_sound(engine, config.SOUNDS_OF_REQUEST, f"Процесс {app_name_to_close} завершен.")
                    break  #выходим, так как нашли и закрыли.
                except psutil.NoSuchProcess:
                    #на случай, если процесс уже закрылся сам.
                    process_found = True
                    engine.say(f"Сэр, не удалось получить доступ к процессу {app_name_to_close}. Возможно, он уже закрыт.")
                    engine.runAndWait()
                    break
        if not process_found:
            engine.say(f"Процесс {app_name_to_close} не найден в системе, Сэр.")
            engine.runAndWait()

        return None
    
    else: #сценарий 2: команда неполная (например, "закрой")
        return "уточнить_закрытие"


def recognize_command(task_name, commands_dict):
    """Распознает наиболее вероятную команду из словаря, используя нечеткий поиск."""
    all_keywords = [] #Цель - взять все кортежи с ключевыми словами (("привет", "здравствуй"), ("погода",), ("время") и т.д.) и сложить их в один-единственный, плоский список.
    for key_tuple in commands_dict.keys(): #commands_dict — это наш главный словарь команд COMMANDS. 
        #Мы сознательно игнорируем содержимое ящиков (skills.greet, skills.open_notepad). На этом этапе нам не важно, что делать. 
        #Нам важно собрать полный список всех возможных команд, по которым мы будем искать совпадение.
        all_keywords.extend(key_tuple) #.extend - делает "плоский" список из отдельных (ключевых) слов, с которыми будет работать fuzzywuzzy.

    try: #используем fuzzywuzzy для поиска наиболее похожего слова.
        best_match = process.extractOne(task_name, all_keywords) #Нахождение лучшего кандидата (extractOne) и затем решение, достаточно ли этот кандидат хорош, чтобы передавать приказ дальше.
        #best_match (перевод) - лучшая схожесть
        keyword = best_match[0] # (Что нашли): В первом поле ([0]) лежит имя самой похожей команды. Например, если сказать "пагода", здесь будет лежать строка "погода".
        confidence = best_match[1] #(Насколько уверены): ([1]) лежит число от 0 до 100 — это "уровень уверенности" в том, что найдена правильная команда.
        #confidence (перевод) = уверенность.
    except:
        return None #если ничего не нашлось - возвращаем пустоту.
    
    if confidence > 75:  #gорог можно будет настроить.
        for key_tuple, func in commands_dict.items(): #нам нужно найти, какой функции соответствует найденное ключевое слово.
            if keyword in key_tuple:
                return func, keyword #возвращаем саму функцию и ключевое слово.   
            #func: Это не строка, а сам объект функции в памяти, например, skills.open_notepad.
            #keyword: Это строка с ключевым словом, например, "блокнот". Мы возвращаем его в основном для отладки и логирования, чтобы видеть, какая именно команда была распознана.
    return None #если уверенность низкая.
       
def  greet(engine, task_name):
    play_sound (engine, config.SOUNDS_OF_GREETINGS)

def check_status(engine, task_name):
    phrase = random.choice(config.STATUS_REPORTS)
    engine.say(phrase)
    engine.runAndWait()

def open_notepad(engine, task_name):
    play_sound (engine, config.SOUNDS_OF_REQUEST)
    try:
        os.startfile('notepad.exe') # os.startfile говорит, чтобы скрипт запустил программу и сразу продолжил работать сам, не ждать окончания запущенной программы.
    except FileNotFoundError:
        engine.say("Сэр, похоже, на этом компьютере нет блокнота.")
        engine.runAndWait()

def open_youtube(engine, task_name):
    play_sound(engine, config.SOUNDS_OF_REQUEST)
    webbrowser.open('https://www.youtube.com/')

def open_telegram(engine, task_name):
    play_sound(engine, config.SOUNDS_OF_REQUEST)
    try:
        os.startfile(config.TELEGRAM_PATH)
    except FileNotFoundError:
        engine.say("Не могу найти программу телеграм по указанному пути.")
        engine.runAndWait()

def open_steam(engine, task_name):
    play_sound(engine, config.SOUNDS_OF_REQUEST)
    try:
        os.startfile(config.STEAM_PATH)
    except FileNotFoundError:
        engine.say("Не могу найти программу стим по указанному пути.")
        engine.runAndWait()

def search_in_google(engine, query):
    play_sound(engine, config.SOUNDS_OF_REQUEST)
    webbrowser.open("https://www.google.com/search?q=" + query) #формирование поисковой ссылки в Google и её открытие.

def get_time(engine_instance, task_name): #пишем движок engine как аргумент для работы.
    """Получает и озвучивает текущее время."""
    now = datetime.datetime.now()
    time_str = now.strftime("%H:%M") #переделываем время в "часы:минуты".
    engine_instance.say("Сейчас " + time_str + ".")
    engine_instance.runAndWait()

def get_date(engine_instance, task_name):
    """Получает и озвучиет текущую дату."""
    now = datetime.datetime.now() 

    month_name = MONTHS[now.month - 1] 

    date_str = f"Сегодня {now.day} {month_name}, Сэр."


    engine_instance.say(date_str)
    engine_instance.runAndWait()
    
def get_weather(engine, task_name):
    city_name = None
    if "в городе" in task_name:
        city_name = task_name.split("в городе")[1].strip()
    elif "погода в" in task_name:
        city_name = task_name.split("погода в")[1].strip()
    elif " в " in task_name:
         try:
            city_name = task_name.split(" в ")[1].strip()
         except IndexError:
            engine.say("Не удалось распознать название города.")
            engine.runAndWait()
            return {'last_action': None} 
    if city_name:
        if city_name.endswith("ве"):
            city_name = city_name[:-1]
            city_name = city_name + "а"
        elif city_name.endswith("е"):
            city_name = city_name[:-1]

    if not city_name:
        url = (f"https://api.openweathermap.org/data/2.5/weather?"
               f"lat={config.WEATHER_CITY_LAT}&lon={config.WEATHER_CITY_LON}&appid={api_keys.OPENWEATHER_API_KEY}"
               f"&units=metric&lang=ru")
    else:
        url = (f"http://api.openweathermap.org/data/2.5/weather?"
               f"q={city_name}&appid={api_keys.OPENWEATHER_API_KEY}&units=metric&lang=ru")

    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            city = data.get('name', city_name)
            description = data["weather"][0]["description"]
            temp = round(data['main']['temp'])
            weather_report = f"В городе {city} сейчас {description}, температура около {temp} градусов."
            engine.say(weather_report)
            engine.runAndWait()
            return {'last_action': 'weather'} #объяснение: если последнее действие было связано с погодой, то и теперь новое действие будет связано с ней, 
            #после слова "погода" система запоминает, что следующий запрос будет связан с именно погодой.
        elif response.status_code == 404:
            engine.say(f"Не могу найти город {city_name}, Сэр.")
            engine.runAndWait()
        else:
            engine.say(f"Ошибка сервера погоды: код {response.status_code}.")
            engine.runAndWait()
    except requests.RequestException:
        engine.say("Проблема с сетью, не могу запросить погоду.")
        engine.runAndWait()


    return {'last_action': None}
