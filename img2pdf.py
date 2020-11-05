import array
from reportlab.pdfgen.canvas import Canvas
from PIL import Image
from datetime import datetime
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram import File, Bot, InputFile
from collections import deque
from io import BytesIO, BufferedReader, BufferedIOBase, BufferedWriter
import sys
import os
import signal
import json

def logToConsole(string):
    print("[{}] {}".format(datetime.now().strftime("%H:%M:%S"), string))
botToken = str(sys.argv[1])
updater = Updater(token=botToken, use_context=True)
bot = Bot(token=botToken)
logToConsole("Bot started.")  
dispatcher = updater.dispatcher
pdfs = {}

def combineArgsIntoSentence(args):
    filename = ""
    for word in args:
        filename+=" "+word
    filename.strip()
    return filename

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
    context.bot.send_message(chat_id=chat, text=getLocalized("upload", user.language_code))

def getPhoto(update, context):
    user = update.message.from_user
    chat = update.effective_chat.id
    if chat not in pdfs:
        author = "{} {}".format(user.first_name if user.language_code=="en" else user.last_name, user.last_name if user.language_code=="en" else user.first_name)
        pdfs[chat] = PDF(chat, user.username, user.language_code, user.username, author)
    pdf = pdfs[update.effective_chat.id]
    pdf.append(update.message.photo[-1].file_id)

def getFile(update, context):
    user = update.message.from_user
    chat = update.effective_chat.id
    if chat not in pdfs:
        author = "{} {}".format(user.first_name if user.language_code=="en" else user.last_name, user.last_name if user.language_code=="en" else user.first_name)
        pdfs[chat] = PDF(chat, user.username, user.language_code, user.username, author)
    pdf = pdfs[update.effective_chat.id]
    pdf.append(update.message.document.file_id)

def create(update, context):
    chat = update.effective_chat.id
    if chat in pdfs:
        pdf = pdfs[chat]
        if context.args: pdf.setFilename(combineArgsIntoSentence(context.args))
        pdf.createPFD()
        pdf.uploadPDF()
        pdfs.pop(chat)   
    else:
        context.bot.send_message(chat_id=chat, text=getLocalized("pdfEmptyError", update.message.from_user.language_code))
   
def delete(update, context):
    user = update.message.from_user.username
    chat = update.effective_chat.id
    if chat in pdfs:
        pdfs.pop(chat)
    context.bot.send_message(chat_id=chat, text=getLocalized("deleted", update.message.from_user.language_code))
    logToConsole("User @{}(chat_id:{}) deleted their pdf.".format(user, chat))

def name(update, context):
    user = update.message.from_user
    chat = update.effective_chat.id
    if chat in pdfs:
        if context.args:
            filename = combineArgsIntoSentence(context.args)
            pdfs[chat].setFilename(filename)
            context.bot.send_message(chat_id=chat, text="{} {}.pdf.".format(getLocalized("nameSet", user.language_code), filename))
        else:
            context.bot.send_message(chat_id=chat, text=getLocalized("noFilenameError", update.message.from_user.language_code))
    else:
        context.bot.send_message(chat_id=chat, text=getLocalized("pdfEmptyError", update.message.from_user.language_code))

dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(CommandHandler('help', help))
dispatcher.add_handler(CommandHandler('upload', upload))
dispatcher.add_handler(CommandHandler('create', create))
dispatcher.add_handler(CommandHandler('name', name))
dispatcher.add_handler(CommandHandler('delete', delete))
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

    def setFilename(self, filename):
        if(not filename.endswith(".pdf")):
          filename+=".pdf"
        self.filename = filename

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
        sent = False
        logToConsole("User @{}(chat_id:{})'s pdf {} was succesfully created.".format(self.user_id, self.chat_id, self.filename))
        bot.send_message(chat_id=self.chat_id, text=getLocalized("sending", self.lc))
        with open(self.filename, 'rb') as file:
            for i in range(10):
                try:
                    bot.send_document(chat_id=self.chat_id, document=file)
                    sent = True
                    break
                except Exception as e:
                    logToConsole("User's @{}(chat_id:{}) pdf {} was not uploaded({}/10) because of an Exception({}).".format(self.user_id, self.chat_id, self.filename, i, e.__class__))
                else:
                    logToConsole("User @{}(chat_id:{}) got theirs pdf {}.".format(self.user_id, self.chat_id, self.filename))
        if not sent:
            bot.send_message(chat_id=self.chat_id, text=getLocalized("uploadingError", self.lc))
        os.remove(self.filename)
        
    def isEmpty(self):
        return len(self.images)==0

with open('localization.json', encoding="utf8") as localizatationFile:
    localizedStrings = json.load(localizatationFile)

def getLocalized(string, lc):
    if lc in localizedStrings:
        dictionary = localizedStrings.get("en")
    else:
        dictionary = localizedStrings.get(lc)
    return dictionary.get(string)
