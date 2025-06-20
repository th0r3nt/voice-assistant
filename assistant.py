import pyttsx3 #запуск голосового ответа от ассистента
import speech_recognition as speechrec ##подключаем голосовой ввод чтобы давать команды ассистенту и даем краткое имя

import webbrowser 
import logging 
import datetime
import requests #работа с API
import random 
import os 
import skills 
import config 
from pydub import AudioSegment #Теперь, к примеру, в функции open_notepad вы можете использовать более короткий вызов без (название функции).(название функции)(фраза)
from pydub.playback import play

from skills import recognize_command

AudioSegment.converter = r"C:\Users\ivanc\voice-assistant\NEED\ffmpeg.exe"

COMMANDS = {

    ("привет", "здравствуй", "моё почтение", "доброе утро", "добрый день"): skills.greet, #Если Джарвис услышит одно из этих слов...  ...он должен выполнить вот эту функцию
    ("как дела", "статус", "как система", "как системы", "система"): skills.check_status, 
    ("youtube", "ютуб"): skills.open_youtube, #вот эта строчка = это кортеж ключей, как и ниже: одна строка = один кортеж ключей
    ("telegram", "телега", "телегу", "тг"): skills.open_telegram,
    ("steam", "стим"): skills.open_steam,
    ("который час", "время", "сколько времени", "сколько сейчас времени"): skills.get_time,
    ("какое сегодня число", "дата", "сегодняшнее число" "какое число", "число"): skills.get_date,
    ("погода",): skills.get_weather,

    #Общие команды действия
    ("запусти", "открой"): skills.launch_app,
    ("закрой", "убей", "убери"): skills.close_app,

    ("пока", "до свидания", "спокойной ночи", "выключись", "отключись"): lambda engine, task_name: "exit" #специальная лямбда-функция для выхода, она однострочная и "анонимная"
}
#для понимания: .keys - вызвать все кортежи (ключевые слова) по типу ("привет", "здравствуй"), ("блокнот",), ("youtube", "ютуб").
#.items - вызвать все функции, по типу skills.greet, skills.open_notepad, skills.open_youtube, сразу со всеми кортежами (ключевыми словами для этой функции)

#кратко: .keys() — когда вам нужны только ключи; .items() — когда вам нужны и ключи, и значения одновременно.


logging.basicConfig( #настройка вывода логов
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("assistant.log", encoding='utf-8'),
        logging.StreamHandler() # Чтобы выводить и в консоль тоже
    ]
)

engine = pyttsx3.init() #указать, что engine = голос, включаем голосовой синтезатор
r = speechrec.Recognizer() #активируем главный "Слуховой сенсор", r - умный слуховой сенсор

context = {} #наше ядро кратковременной памяти

#приветствие (один раз в начале)
sound_path = random.choice(config.SOUNDS_OF_GREETINGS)
try:
    audio_segment = AudioSegment.from_mp3(sound_path)
    play(audio_segment)
except Exception as error:
    print(f"Ошибка воспроизведения звука: {error}")
    phrase = random.choice(config.GREETINGS)
    engine.say(phrase)
    engine.runAndWait()

def clear_console(): #ОСТАВИТЬ СРАЗУ ПЕРЕД НАЧАЛОМ БЕСКОНЕЧНОГО ЦИКЛА, ИНАЧЕ НЕ БУДЕТ РАБОТАТЬ
    """Очищает консоль в зависимости от операционной системы."""
    if os.name == 'nt':
        os.system('cls')
    else:
        os.system('clear')
clear_console()

#НАЧАЛО БЕСКОНЕЧНОГО ЦИКЛА
while True: #while (перевод "пока") ИСТИНА = начало бесконечного цикла, будет повторяться раз за разом
    with speechrec.Microphone() as sourse:
        r.adjust_for_ambient_noise(sourse, duration=1.0)
        audio = r.listen(sourse) #метод listen() "слушает" source (источник) = микрофон, КОМАНДА СЛУШАТЬ

    try: #распознаем речь
        full_phrase = r.recognize_google(audio, language="ru-RU").lower() #.lower преобразует текст в ниж. регистр
        #объект "r" (слуховой сенсор) берет сырую аудиозапись audio, он отправляет на сервера Google, 
        #там суперпк анализирует и превращает в текст, потом отправляет сюда, а наша программа получает текст и кладет в full.phrase.

        logging.info(f"Распознано: {full_phrase}.") #для отладки, логов.


        #НАЧАЛО НОВОГО, УЛУЧШЕННОГО БЛОКА КОНТЕКСТА.

        clean_phrase = full_phrase.replace(config.ASSISTANT_NAME, "").strip() #сначала очищаем фразу от имени ассистента, чтобы оно нам не мешало.

         #теперь проверяем, есть ли активный контекст.
        if "требуется_уточнение" in context:
            action = context["требуется_уточнение"]
            if action == "launch_app":
                full_command = "запусти " + clean_phrase
                skills.launch_app(engine, full_command)
            elif action == "close_app":
                full_command = "закрой " + clean_phrase
                skills.close_app(engine, full_command)
            
            context.clear()
            continue # Контекст обработан, начинаем сначала.

        elif "last_action" in context and context['last_action'] == "weather": #если последним действием была погода, любая следующая фраза - это город.
            skills.get_weather(engine, full_phrase) #передаем фразу целиком, пусть get_weather разбирается.
            context.clear()
            continue #контекст обработан, начинаем сначала.



        if full_phrase.startswith(config.ASSISTANT_NAME): #мозг просыпается, и тут главная проверка: начинается ли фраза пользователя с "Ассистент"?
            task_name = full_phrase.replace(config.ASSISTANT_NAME, "").strip() #отрезаем "Ассистент" во фразе пользователя, чтобы получилоть чистый запрос.
            #.strip - обрезание пробелов.
            recognized_data = recognize_command(task_name, COMMANDS)
            if recognized_data:
                command_func, keyword = recognized_data

                print(f"Распознана команда: {keyword} c функцией {command_func.__name__}") #лог для отладки.

                #выполняем распознанную функцию.
                result = command_func(engine, task_name) #передаем task_name, чтобы функции могли извлечь детали.
                if result == "уточнить_запуск":
                    engine.say("Уточните, Сэр. Какое приложение мне запустить?")
                    engine.runAndWait()
                    context["требуется_уточнение"] = 'launch_app'
                elif result == "уточнить_закрытие":
                    engine.say("Уточните, Сэр. Какое приложение мне закрыть?")
                    engine.runAndWait()
                    context ["требуется_уточнение"] = "close_app"
                elif isinstance(result, dict):
                    context.update(result)
                if result == "exit":
                    engine.say("До свидания, Сэр!")
                    engine.runAndWait()
                    exit()

            else: #если ничего не распознано с достаточной уверенностью.
                phrase = random.choice(config.UNKNOWN_COMMAND)
                engine.say(phrase)
                engine.runAndWait()

    except speechrec.UnknownValueError: #эта ошибка возникает, если Google не смог распознать речь
        pass #если распознание нужного начального слова (к примеру, "Ассистент") не удалось - ничего не делаем
    except speechrec.RequestError as e: #Эта ошибка возникает, если есть проблемы с интернетом
        engine.say("Проблема с доступом в интернет, Сэр.")
        engine.runAndWait()


phrase = random.choice(EXIT_PHRASES)
engine.say(phrase)
engine.runAndWait()