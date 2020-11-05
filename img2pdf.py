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
    """Prints the specified string with the current time."""
    print(f'[{datetime.now().strftime("%H:%M:%S")}] {string}')

botToken = str(sys.argv[1])
updater = Updater(token=botToken, use_context=True)
bot = Bot(token=botToken)
logToConsole("Bot started.")  
dispatcher = updater.dispatcher
pdfs = {}

def combineArgsIntoSentence(args):
    """Combines all the args into a string with spaces as divider. Returns that string."""
    filename = ""
    for word in args:
        filename+=" "+word
    filename.strip()
    return filename

def start(update, context):
    """Sends the welcome message to the user."""
    context.bot.send_message(chat_id=update.effective_chat.id, text=getLocalized("start", update.effective_user.language_code))
    logToConsole("User @{username}(chat_id:{chat_id}) initalized the bot.".format(username = update.message.from_user.username, chat_id = update.effective_chat.id))
    
def help(update, context):
    """Sends the guide to the user."""
    photo = open("howto.png", 'rb')
    context.bot.send_photo(chat_id=update.effective_chat.id, photo=photo)
    photo.close()

def unknown(update, context):
    """Sends the unknown command message to the user."""
    context.bot.send_message(chat_id=update.effective_chat.id, text=getLocalized("unknown", update.effective_user.language_code))

def upload(update, context):
    """Deprecated! Send the deprecated message to the user."""
    user = update.message.from_user
    chat = update.effective_chat.id
    context.bot.send_message(chat_id=chat, text=getLocalized("upload", user.language_code))

def getPhoto(update, context):
    """Downloads a photo and adds it to the photos queue."""
    user = update.message.from_user
    chat = update.effective_chat.id
    if chat not in pdfs:
        author = "{} {}".format(user.first_name if user.language_code=="en" else user.last_name, user.last_name if user.language_code=="en" else user.first_name)
        pdfs[chat] = PDF(chat, user.username, user.language_code, user.username, author)
    pdf = pdfs[update.effective_chat.id]
    pdf.append(update.message.photo[-1].file_id)

def getFile(update, context):
    """Downloads a document and adds it to the photos queue."""
    user = update.message.from_user
    chat = update.effective_chat.id
    if chat not in pdfs:
        author = "{} {}".format(user.first_name if user.language_code=="en" else user.last_name, user.last_name if user.language_code=="en" else user.first_name)
        pdfs[chat] = PDF(chat, user.username, user.language_code, user.username, author)
    pdf = pdfs[update.effective_chat.id]
    pdf.append(update.message.document.file_id)

def create(update, context):
    """combines the photos into a pdf file and sends that to the user."""
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
    """Deletes the current pdf from the pdfs queue."""
    user = update.message.from_user.username
    chat = update.effective_chat.id
    if chat in pdfs:
        pdfs.pop(chat)
    context.bot.send_message(chat_id=chat, text=getLocalized("deleted", update.message.from_user.language_code))
    logToConsole("User @{username}(chat_id:{chat_id}) deleted their pdf.".format(username = user, chat_id = chat))

def name(update, context):
    """Sets the filename of the current pdf"""
    user = update.message.from_user
    chat = update.effective_chat.id
    if chat in pdfs:
        if context.args:
            filename = combineArgsIntoSentence(context.args)
            pdfs[chat].setFilename(filename)
            context.bot.send_message(chat_id=chat, text="{prompt} {filename}.pdf.".format(prompt = getLocalized("nameSet", user.language_code), filename = filename))
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
        logToConsole(f"User @{user_id}(chat_id:{chat_id}) created {filename}.")

    def setFilename(self, filename):
        if(not filename.endswith(".pdf")):
          filename+=".pdf"
        self.filename = filename

    def append(self, image):
        bot.send_message(chat_id=self.chat_id, text=getLocalized("success", self.lc))
        self.images.append(image)

    def createPFD(self):
        logToConsole(f"User @{self.user_id}(chat_id:{self.chat_id}) uploaded and combined the pictures into {self.filename}.")
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
        logToConsole(f"User @{self.user_id}(chat_id:{self.chat_id})'s pdf {self.filename} was succesfully created.")
        bot.send_message(chat_id=self.chat_id, text=getLocalized("sending", self.lc))
        with open(self.filename, 'rb') as file:
            for i in range(10):
                try:
                    bot.send_document(chat_id=self.chat_id, document=file)
                    sent = True
                    break
                except Exception as e:
                    logToConsole(f"User @{self.user_id}(chat_id:{self.chat_id})'s pdf {self.filename} was not uploaded({i}/10) because of an Exception({e.__class__}).")
                else:
                    logToConsole(f"User @{self.user_id}(chat_id:{self.chat_id}) got theirs pdf {self.filename}.")
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
