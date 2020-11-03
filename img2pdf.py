import array
from reportlab.pdfgen.canvas import Canvas
from PIL import Image
from datetime import datetime
from reportlab.lib.pagesizes import A4
from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler, Filters
from telegram import File, Bot, InputFile
from collections import deque
from io import BytesIO, BufferedReader, BufferedIOBase, BufferedWriter
import sys
import os
import signal

def logToConsole(string):
    print("[{}] {}".format(datetime.now().strftime("%H:%M:%S"), string))
botToken = str(sys.argv[1])
updater = Updater(token=botToken, use_context=True)
bot = Bot(token=botToken)
logToConsole("Bot started.")  
dispatcher = updater.dispatcher
pdfs = {}

def start(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text=getLocalized("start", update.effective_user.language_code))
    logToConsole("User @{}(chat_id:{}) initalized the bot.".format(update.message.from_user.username, update.effective_chat.id))
    
def help(update, context):
    photo = open("howto.png", 'rb')
    context.bot.send_photo(chat_id=update.effective_chat.id, photo=photo)
    photo.close()
def unknown(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text=getLocalized("unknown", update.effective_user.language_code))

def upload(update, context):
    user = update.message.from_user
    chat = update.effective_chat.id
    author = "{} {}".format(user.first_name if user.language_code=="en" else user.last_name, user.last_name if user.language_code=="en" else user.first_name)
    filename = ""
    if(not context.args):
        context.args = ["{}.pdf".format(user.username)]
    for word in context.args:
        filename+=" "+word
    filename.strip()
    pdfs[chat] = PDF(chat, user.username, user.language_code, filename, author)
    context.bot.send_message(chat_id=chat, text=getLocalized("upload", user.language_code))

def getPhoto(update, context):
    pdf = pdfs[update.effective_chat.id]
    pdf.append(update.message.photo[-1].file_id)

def getFile(update, context):
    pdf = pdfs[update.effective_chat.id]
    pdf.append(update.message.document.file_id)

def create(update, context):
    chat = update.effective_chat.id
    try:
        pdf = pdfs[chat]
        if pdf.isEmpty():
            context.bot.send_message(chat_id=chat, text=getLocalized("pdfEmptyError", update.message.from_user.language_code))
        else:
            pdf.createPFD()
            pdf.uploadPDF()
            pdfs.pop(chat)
    except KeyError:
        context.bot.send_message(chat_id=chat, text=getLocalized("fileNotInitiatedError", update.message.from_user.language_code))
        pass

dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(CommandHandler('help', help))
dispatcher.add_handler(CommandHandler('upload', upload))
dispatcher.add_handler(CommandHandler('create', create))
dispatcher.add_handler(MessageHandler(Filters.command, unknown))
dispatcher.add_handler(MessageHandler(Filters.photo & (~Filters.command), getPhoto))
dispatcher.add_handler(MessageHandler(Filters.document.category("image") & (~Filters.command), getFile))

updater.start_polling()

class PDF:
    def __init__(self, chat_id, user_id, lc, filename, author):
        self.chat_id = chat_id
        self.user_id = user_id
        self.lc = lc
        if(not filename.endswith(".pdf")):
            filename+=".pdf"
        self.filename = filename
        self.images = deque()
        self.author = author
        logToConsole("User @{}(chat_id:{}) created {}.".format(user_id, chat_id, filename))

    def append(self, image):
        bot.send_message(chat_id=self.chat_id, text=getLocalized("success", self.lc))
        self.images.append(image)

    def createPFD(self):
        logToConsole("User @{}(chat_id:{}) uploaded and combined the pictures into {}.".format(self.user_id, self.chat_id, self.filename))
        canvas = Canvas(filename=self.filename)
        canvas.setTitle(self.filename)
        canvas.setAuthor(self.author)
        for image in self.images:
            bytes = BytesIO(bot.getFile(image).download_as_bytearray())  
            page = Image.open(bytes).convert("RGBA")
            bytes.close()
            page_width, page_height = page.size
            draw_width, draw_height = page_width, page_height
            if page_width > page_height:
                canvas.setPageSize((draw_width, draw_height))
            else:
                canvas.setPageSize((draw_width, draw_height))
            canvas.drawInlineImage(page, 0, 0, width=draw_width, height=draw_height)
            canvas.showPage()
        canvas.save()

    def uploadPDF(self):
        file = open(self.filename, 'rb')
        logToConsole("User @{}(chat_id:{})'s pdf {} was succesfully created.".format(self.user_id, self.chat_id, self.filename))
        bot.send_message(chat_id=self.chat_id, text=getLocalized("sending", self.lc))
        for i in range(10):
            try:
                bot.send_document(chat_id=self.chat_id, document=file)
                break
            except Exception as e:
                bot.send_message(chat_id=self.chat_id, text=getLocalized("uploadingError", self.lc))
                logToConsole("User's @{}(chat_id:{}) pdf {} was not uploaded({}/10) because of an Exception({}).".format(self.user_id, self.chat_id, self.filename, i, e.__class__))
        file.close()
        logToConsole("User @{}(chat_id:{}) got theirs pdf {}.".format(self.user_id, self.chat_id, self.filename))
        os.remove(self.filename)

    def isEmpty(self):
        print(self.images.count)
        return self.images.count==0


localizedStrings = {
    "en" : {
        "start" : "A bot for converting images to a pdf file.\nTo start, use the command\n/upload <Name>.\nMade by @coutaq.",
        "upload" : "Upload images up to 20mb per image.\nWhen you're done use /create to create the pdf",
        "success": "Photo succesfully uploaded!",
        "sending": "Uploading the pdf!",
        "unknown": "Sorry, I didn't understand that command.",
        "fileNotInitiatedError" : "You must first use the /upload command before using /create.",
        "pdfEmptyError": "You cannot create an empty pdf!",
        "uploadingError": "Upload failed!"
  },
    "ru" : {
        "start" : "Бот для создания pdf из картинок.\nЧтобы начать, используйте комманду\n/upload <Название>.\nMade by @coutaq.",
        "upload" : "Загрузите картинки.\nКогда загрузите, используйте /create",
        "success": "Фото загружено!",
        "sending": "Отправляю .pdf!",
        "unknown": "Извините, я такое не умею.",
        "fileNotInitiatedError" : "Перед использованием этой команды, нужно создать файл с помощью /upload.",
        "pdfEmptyError": "Нельзя создать пустой документ!",
        "uploadingError": "Не удалось отправить документ!"
  },
   "uk" : {
        "start" : "Бот для створення pdf з картинок.\nДля того щоб розпочати, використовуйте комманду\n/upload <Назва>.\nMade by @coutaq, translated by @Imllush.",
        "upload" : "Завантажте картинки.\nКоли завантажити, використовуйте /create",
        "success": "Картинка завантажена!",
        "sending": "Відправляю .pdf!",
        "unknown": "Вибачте, я таке не вмію.",
        "fileNotInitiatedError" : "Перед використанням цієї команди, потрібно створити файл за допомогою /upload.",
        "pdfEmptyError": "Неможливо створити пустий документ!",
        "uploadingError": "Не вдалося відправити документ!"
  },
}
def getLocalized(string, lc):
    if lc in localizedStrings:
        dictionary = localizedStrings.get(lc)
    else:
        dictionary = localizedStrings.get("en")
    return dictionary.get(string)
